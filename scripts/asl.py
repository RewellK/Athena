"""Run a reviewed ASL JSON file locally. Writes require its exact approval hash."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from memory.database import MemoryDB
from bootstrap import AthenaBootstrap
from runtime.process_lease import foreground_session
from semantic_language import ASLInterpreter


def main():
    parser = argparse.ArgumentParser(description="ASL 1 — operações declarativas de memória")
    parser.add_argument("file", type=Path)
    parser.add_argument("--approve", help="Hash do programa revisado, retornado na primeira execução")
    args = parser.parse_args()
    program = json.loads(args.file.read_text())
    os.chdir(ROOT)
    os.umask(0o077)
    with foreground_session():
        db = MemoryDB()
        try:
            AthenaBootstrap(db).run()
            result = ASLInterpreter(db).execute(program, args.approve)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        finally:
            db.close()


if __name__ == "__main__":
    main()
