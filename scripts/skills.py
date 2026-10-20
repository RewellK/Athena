import argparse
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from agency.local_tasks import LocalTasks
from capabilities.skill_backend import SkillBackend
from core.settings import Settings
from llm.provider import OllamaProvider
from runtime.process_lease import foreground_session


def main():
    parser=argparse.ArgumentParser(description='Backend de habilidades locais verificáveis')
    parser.add_argument('action',choices=['list','propose','design','verify','activate','run'])
    parser.add_argument('--file',type=Path)
    parser.add_argument('--request')
    parser.add_argument('--id')
    parser.add_argument('--approve')
    args=parser.parse_args()
    program=json.loads(args.file.read_text()) if args.file else None
    os.chdir(ROOT); os.umask(0o077)
    with foreground_session():
        backend=SkillBackend(LocalTasks(),OllamaProvider(Settings()))
        if args.action=='list': result=backend.list()
        elif args.action=='propose': result=backend.propose(program)
        elif args.action=='design': result=backend.learn(args.request,allow_local_policy=Settings().get('autonomousLocalSkillLearning',False))
        elif args.action=='verify': result=backend.verify(args.id)
        elif args.action=='activate': result=backend.activate(args.id,args.approve)
        else: result=backend.run(args.id)
        print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
