"""Install the built app and migrate local state, preserving the original copy."""
from pathlib import Path
import argparse
import json
import hashlib
import os
import plistlib
import shutil
import sqlite3
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from runtime.process_lease import foreground_session
from desktop.service import specification,LABEL


def migrate(source,home):
    home.mkdir(parents=True,exist_ok=True,mode=0o700)
    if (home/'knowledge.db').exists():
        raise RuntimeError('Já existe memória no destino. Não vou sobrescrever o banco.')
    for name in ('config','personality','.athena_workspace'):
        if (source/name).exists():shutil.copytree(source/name,home/name,dirs_exist_ok=True)
    (home/'logs').mkdir(exist_ok=True,mode=0o700)
    state=source/'logs/runtime_state.json'
    if state.exists():shutil.copy2(state,home/'logs/runtime_state.json')
    with sqlite3.connect('file:'+str(source/'knowledge.db')+'?mode=ro',uri=True) as before:
        with sqlite3.connect(home/'knowledge.db') as after:
            before.backup(after)
            if after.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RuntimeError('Backup SQLite inválido')
    (home/'knowledge.db').chmod(0o600)
    for name in ('config/settings.json','personality/identity.json'):
        if (home/name).exists():(home/name).chmod(0o600)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--app',type=Path,default=ROOT/'dist/Athena.app')
    parser.add_argument('--destination',type=Path,default=Path.home()/'Applications/Athena.app')
    parser.add_argument('--data-home',type=Path,default=Path.home()/'Library/Application Support/Athena')
    parser.add_argument('--migrate-from',type=Path)
    parser.add_argument('--enable-voice',action='store_true')
    parser.add_argument('--update',action='store_true',help='Atualizar aplicativo próprio, preservando a cópia anterior')
    parser.add_argument('--resume',action='store_true',help='Retomar cópia já concluída, sem sobrescrever dados')
    args=parser.parse_args()
    app=args.app.resolve();destination=args.destination.expanduser().absolute();home=args.data_home.expanduser().absolute()
    subprocess.run(['codesign','--verify','--deep','--strict',str(app)],check=True)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists() and args.update:
        subprocess.run(['launchctl','bootout',f'gui/{os.getuid()}/'+LABEL],capture_output=True)
        time.sleep(2)
        backup=destination.with_name('Athena.previous.'+str(int(time.time()))+'.app')
        destination.rename(backup)
    if destination.exists():
        if not args.resume:raise RuntimeError('Já existe Athena.app no destino; use --resume apenas para retomar esta instalação.')
        relative='Contents/MacOS/Athena'
        if hashlib.sha256((app/relative).read_bytes()).digest()!=hashlib.sha256((destination/relative).read_bytes()).digest():raise RuntimeError('Aplicativo existente difere desta compilação.')
    else:subprocess.run(['ditto',str(app),str(destination)],check=True)
    target=Path.home()/'Library/LaunchAgents'/(LABEL+'.plist');domain=f'gui/{os.getuid()}'
    old=target.read_bytes() if target.exists() else None
    source=args.migrate_from.resolve() if args.migrate_from else None
    from contextlib import nullcontext
    with foreground_session(source/'logs') if source else nullcontext():
        if source:
            if args.resume and (home/'knowledge.db').exists():
                with sqlite3.connect('file:'+str(home/'knowledge.db')+'?mode=ro',uri=True) as db:
                    if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RuntimeError('Banco de destino inválido')
            else:migrate(source,home)
        else:
            home.mkdir(parents=True,exist_ok=True,mode=0o700);(home/'logs').mkdir(exist_ok=True,mode=0o700)
        if args.enable_voice:
            config=home/'config/settings.json'
            values=json.loads(config.read_text());values.update(voiceEnabled=True,voiceSpeakResponses=True)
            config.write_text(json.dumps(values,ensure_ascii=False,indent=2))
        if old:
            backup=home/'backups';backup.mkdir(exist_ok=True,mode=0o700)
            (backup/('launchagent-before-app-'+str(int(time.time()))+'.plist')).write_bytes(old)
        subprocess.run(['launchctl','bootout',domain+'/'+LABEL],capture_output=True)
        target.parent.mkdir(parents=True,exist_ok=True)
        from desktop.helpers import prepare_helpers,resident_executable
        prepare_helpers(destination,home)
        target.write_bytes(plistlib.dumps(specification(resident_executable(home),home)));target.chmod(0o600)
        def bootstrap():
            subprocess.run(['launchctl','enable',domain+'/'+LABEL],capture_output=True)
            for attempt in range(5):
                result=subprocess.run(['launchctl','bootstrap',domain,str(target)],capture_output=True,text=True)
                if result.returncode==0:return
                if subprocess.run(['launchctl','print',domain+'/'+LABEL],capture_output=True).returncode==0:return
                time.sleep(attempt+1)
            raise RuntimeError('launchd: '+result.stderr.strip())
        try:bootstrap()
        except Exception:
            if old:target.write_bytes(old);subprocess.run(['launchctl','bootstrap',domain,str(target)],capture_output=True)
            raise
        if source:
            pointer=source/'.athena-installation.json'
            pointer.write_text(json.dumps({'data_home':str(home),'application':str(destination)}));pointer.chmod(0o600)
    print(json.dumps({'application':str(destination),'data_home':str(home),'original_preserved':str(source) if source else None}))


if __name__=='__main__':main()
