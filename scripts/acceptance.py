"""Reproducible live acceptance in a temporary copy, never the personal database."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description='Teste real local com banco temporário')
    parser.add_argument('--model')
    parser.add_argument('--url')
    parser.add_argument('--report',default=str(ROOT/'logs/live_acceptance.json'))
    args=parser.parse_args()
    output=Path(args.report).expanduser().absolute()
    report={'checks':[],'passed':False}
    with tempfile.TemporaryDirectory(prefix='athena-acceptance-') as temporary:
        root=Path(temporary)/'Athena'
        shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns('.git','venv','__pycache__','logs','*.db','*.db-shm','*.db-wal','.athena_workspace'))
        path=root/'config/settings.json';settings=json.loads(path.read_text())
        settings.update(agentBackend='openjarvis',voiceEnabled=False,messageReceivedSoundEnabled=False,
            localDesktopNotifications=False,computerToolsEnabled=False,browserToolsEnabled=False,allowExternalRequests=False)
        if args.model: settings['ollamaModel']=args.model
        if args.url: settings['ollamaUrl']=args.url
        path.write_text(json.dumps(settings));os.chdir(root);sys.path.insert(0,str(root))
        from brain.orchestrator import Athena
        from runtime.process_lease import close_core
        athena=Athena()
        def turn(text):
            started=time.monotonic();response=athena.chat(text)
            item={'request':text,'seconds':round(time.monotonic()-started,2),'response':response,
                  'metadata':athena.last_response_metadata.copy()}
            report['checks'].append(item);print(json.dumps(item,ensure_ascii=False),flush=True)
            return response
        try:
            turn('Crie uma nota contendo apenas o texto entre aspas: "Revisar o projeto amanhã". Em seguida faça um backup da memória.')
            tasks=athena.local_tasks.list()
            notes=[task for task in tasks if task['kind']=='note' and task['status']=='completed']
            backups=[task for task in tasks if task['kind']=='backup' and task['status']=='completed']
            action_ok=bool(notes and backups)
            for task in notes+backups:
                result=json.loads(task['result']);data=Path(result['path']).read_bytes()
                action_ok=action_ok and hashlib.sha256(data).hexdigest()==result['sha256']
                if task['kind']=='note': action_ok=action_ok and data.decode().strip()=='Revisar o projeto amanhã'
            report['verified_note_and_backup']=action_ok
            report['learned_skills']=athena.agent_runtime.catalog.procedures.list()
            turn('Guarde que minha cor favorita é azul.')
            turn('Minha cor favorita agora é verde. Atualize a mesma propriedade na memória.')
            report['memory_versions']=athena.agent_runtime.catalog.memory.history('Rewell')
            athena.conversation_context.store.clear();close_core(athena);athena=Athena()
            response=turn('Qual é minha cor favorita?')
            report['recalled_after_restart']='verde' in response.casefold()
            facts=athena.agent_runtime.catalog.memory.search('cor favorita')['facts']
            report['active_green_fact']=any(fact['fact'].casefold()=='verde' for fact in facts)
            report['passed']=bool(action_ok and report['learned_skills'] and report['recalled_after_restart'] and report['active_green_fact'])
        finally:
            close_core(athena)
    os.chdir(ROOT)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2));print('Relatório:',output)
    return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
