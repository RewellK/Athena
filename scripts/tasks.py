"""Explicit local tasks, persistently scheduled for resident or manual run."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from agency.local_tasks import LocalTasks
from runtime.process_lease import foreground_session


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['note','reminder','backup','list','run','cancel'])
    parser.add_argument('--text',default='')
    parser.add_argument('--at',help='Data ISO com fuso, exemplo 2026-10-20T09:00:00-03:00')
    parser.add_argument('--id')
    args=parser.parse_args()
    due=None
    if args.at:
        parsed=datetime.fromisoformat(args.at)
        if parsed.tzinfo is None:
            parser.error('Use data ISO com fuso horário explícito')
        due=parsed.timestamp()
    os.chdir(ROOT); os.umask(0o077)
    with foreground_session():
        tasks=LocalTasks()
        if args.action=='list': result=tasks.list()
        elif args.action=='run': result=tasks.run_once()
        elif args.action=='cancel': result={'cancelled':tasks.cancel(args.id)}
        else: result={'scheduled':tasks.schedule(args.action,args.text,due)}
        print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
