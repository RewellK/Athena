"""Explicit tools without LLM; same policy, validation and execution evidence."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from runtime.process_lease import foreground_session,close_core


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('tool',nargs='?')
    parser.add_argument('--arguments',default='{}')
    parser.add_argument('--arguments-file')
    args=parser.parse_args()
    os.chdir(ROOT);os.umask(0o077)
    from brain.orchestrator import Athena
    from integrations.openjarvis.adapter import OpenJarvisRuntime
    with foreground_session():
        athena=Athena()
        try:
            runtime=OpenJarvisRuntime(athena);athena.agent_runtime=runtime
            if not args.tool:
                print(json.dumps([d.schema() for d in runtime.catalog.definitions.values()],ensure_ascii=False,indent=2));return
            arguments=json.loads(Path(args.arguments_file).read_text() if args.arguments_file else args.arguments)
            print(runtime.run_tool(args.tool,arguments))
        finally:close_core(athena)


if __name__=='__main__':main()
