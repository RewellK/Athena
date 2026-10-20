"""Per-user launchd service for a bundled executable; no root or network listener."""
import os
from pathlib import Path
import plistlib
import subprocess
import sys
from desktop.paths import data_home

LABEL='local.athena.resident'


def specification(executable=None,home=None):
    home=Path(home or data_home())
    from desktop.helpers import resident_executable
    helper=resident_executable(home)
    if executable is None and helper.exists():executable=helper
    return {'Label':LABEL,'ProgramArguments':[str(executable or sys.executable),'--resident'],
            'WorkingDirectory':str(home),'EnvironmentVariables':{'ATHENA_HOME':str(home)},
            'RunAtLoad':True,'KeepAlive':{'SuccessfulExit':False},'ThrottleInterval':30,
            'ExitTimeOut':15,'ProcessType':'Background','Umask':0o077,
            'StandardOutPath':str(home/'logs/resident.stdout.log'),
            'StandardErrorPath':str(home/'logs/resident.stderr.log')}


def service_name():return f'gui/{os.getuid()}/{LABEL}'
def target_path():return Path.home()/'Library/LaunchAgents'/(LABEL+'.plist')


def installed():
    target=target_path()
    return target.exists() and plistlib.loads(target.read_bytes()).get('ProgramArguments')==specification()['ProgramArguments']


def install():
    if sys.platform!='darwin' or not getattr(sys,'frozen',False):return
    target=target_path();target.parent.mkdir(parents=True,exist_ok=True)
    desired=specification()
    if target.exists():
        previous=plistlib.loads(target.read_bytes())
        if previous.get('ProgramArguments')!=desired['ProgramArguments']:
            raise RuntimeError('Outro diretório usa o serviço Athena. Migre a instalação antes de abrir este aplicativo.')
    else:
        target.write_bytes(plistlib.dumps(desired));target.chmod(0o600)
    status=subprocess.run(['launchctl','print',service_name()],capture_output=True)
    if status.returncode:
        subprocess.run(['launchctl','bootstrap',f'gui/{os.getuid()}',str(target)],check=True,capture_output=True)


def uninstall():
    if sys.platform!='darwin':return
    if not installed():raise RuntimeError('Este aplicativo não é o proprietário do serviço instalado.')
    subprocess.run(['launchctl','bootout',service_name()],capture_output=True)
    target_path().unlink(missing_ok=True)
