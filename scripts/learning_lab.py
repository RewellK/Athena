"""Inspect or prepare local training examples; does not train weights."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from agency.local_tasks import LocalTasks
from integrations.openjarvis.store import ExecutionStore
from integrations.openjarvis.learning_lab import LearningLab
from runtime.process_lease import foreground_session


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['status','review','export'])
    parser.add_argument('--run-id')
    parser.add_argument('--accept',action='store_true')
    parser.add_argument('--note',default='')
    args=parser.parse_args()
    os.chdir(ROOT);os.umask(0o077)
    with foreground_session():
        tasks=LocalTasks();ExecutionStore(tasks);lab=LearningLab(tasks)
        if args.action=='status': result=lab.status()
        elif args.action=='export': result=lab.export()
        else:
            if not args.run_id: parser.error('--run-id é necessário')
            result=lab.review(args.run_id,args.accept,args.note)
        print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
