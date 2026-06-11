#!/usr/bin/env python3
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bootstrap import AthenaBootstrap
from memory.database import MemoryDB


CONFIRMATION_TEXT = "RESET_KNOWLEDGE_DB"


def reset_knowledge_db(db_path="knowledge.db", backup_root="backups", confirm=""):
    if confirm != CONFIRMATION_TEXT:
        raise ValueError(f"Confirmação obrigatória ausente. Use --confirm {CONFIRMATION_TEXT}.")

    db_path = Path(db_path)
    backup_root = Path(backup_root)
    timestamp = datetime.now().strftime("db_reset_%Y%m%d_%H%M%S")
    backup_dir = backup_root / timestamp
    backup_dir.mkdir(parents=True, exist_ok=False)

    related_paths = [db_path, Path(str(db_path) + "-wal"), Path(str(db_path) + "-shm")]
    backed_up = []
    for path in related_paths:
        if path.exists():
            destination = backup_dir / path.name
            shutil.copy2(path, destination)
            backed_up.append(str(destination))

    for path in related_paths:
        if path.exists():
            path.unlink()

    memory = MemoryDB(str(db_path))
    try:
        AthenaBootstrap(memory).run()
    finally:
        memory.close()

    return {
        "db_path": str(db_path),
        "backup_dir": str(backup_dir),
        "backed_up": backed_up,
        "recreated": db_path.exists(),
    }


def main():
    parser = argparse.ArgumentParser(description="Reset seguro do banco local da Athena com backup obrigatório.")
    parser.add_argument("--db", default="knowledge.db", help="Caminho do banco SQLite da Athena.")
    parser.add_argument("--backup-dir", default="backups", help="Diretório onde o backup será criado.")
    parser.add_argument("--confirm", default="", help=f"Texto obrigatório: {CONFIRMATION_TEXT}")
    args = parser.parse_args()

    try:
        result = reset_knowledge_db(args.db, args.backup_dir, args.confirm)
    except ValueError as error:
        print(f"Reset cancelado: {error}")
        print("Nada foi alterado.")
        return 2

    print("Reset seguro concluído.")
    print(f"Banco recriado: {result['db_path']}")
    print(f"Backup: {result['backup_dir']}")
    if result["backed_up"]:
        print("Arquivos preservados:")
        for path in result["backed_up"]:
            print(f"- {path}")
    else:
        print("Nenhum banco anterior existia para backup.")
    print("Reinicie a GUI para garantir que ela use a nova conexão SQLite.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
