"""Real bounded local execution. Only declared tools; no arbitrary paths or code."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import threading
import uuid


class LocalTasks:
    KINDS = {'note', 'reminder', 'backup'}

    def __init__(self, database='knowledge.db', workspace='.athena_workspace', notifications=False):
        self.notifications = notifications
        self._run_lock=threading.RLock()
        self.database = str(database)
        self.workspace = Path(workspace).absolute()
        if self.workspace.is_symlink():
            raise ValueError('Workspace não pode ser link simbólico')
        self.workspace.mkdir(mode=0o700, parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS local_tasks (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL,
                due REAL NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                result TEXT, created REAL NOT NULL, completed REAL)''')
            # A process killed after claiming a task may resume it. Outputs use task IDs.
            db.execute("UPDATE local_tasks SET status='pending' WHERE status='running'")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def schedule(self, kind, text='', due=None):
        if kind not in self.KINDS:
            raise ValueError('Ferramenta local não permitida')
        if not isinstance(text, str) or len(text) > 8000 or (kind != 'backup' and not text.strip()):
            raise ValueError('Texto necessário, até 8000 caracteres')
        due = time.time() if due is None else float(due)
        if not time.time()-60 <= due <= time.time()+366*86400:
            raise ValueError('Data fora do intervalo permitido de um ano')
        task_id = uuid.uuid4().hex
        with self.connect() as db:
            db.execute('INSERT INTO local_tasks(id,kind,payload,due,status,created) VALUES (?,?,?,?,?,?)',
                (task_id,kind,json.dumps({'text':text},ensure_ascii=False),due,'pending',time.time()))
        return task_id

    def list(self):
        with self.connect() as db:
            rows = db.execute('SELECT id,kind,due,status,result FROM local_tasks ORDER BY created DESC LIMIT 100').fetchall()
        return [dict(zip(('id','kind','due','status','result'), row)) for row in rows]

    def cancel(self, task_id):
        with self.connect() as db:
            cursor = db.execute("UPDATE local_tasks SET status='cancelled' WHERE id=? AND status IN ('pending','failed')", (task_id,))
        return bool(cursor.rowcount)

    def run_once(self):
        with self._run_lock:
            return self._run_once()

    def _run_once(self):
        completed, failed = 0, 0
        with self.connect() as db:
            rows = db.execute("SELECT id,kind,payload FROM local_tasks WHERE status='pending' AND due<=? AND attempts<3 ORDER BY due LIMIT 5", (time.time(),)).fetchall()
        for task_id, kind, payload in rows:
            with self.connect() as db:
                claimed = db.execute("UPDATE local_tasks SET status='running',attempts=attempts+1 WHERE id=? AND status='pending'", (task_id,)).rowcount
            if not claimed:
                continue
            try:
                result = self._execute(task_id,kind,json.loads(payload))
                with self.connect() as db:
                    db.execute("UPDATE local_tasks SET status='completed',result=?,completed=? WHERE id=?", (json.dumps(result,ensure_ascii=False),time.time(),task_id))
                completed += 1
            except Exception as error:
                with self.connect() as db:
                    db.execute("UPDATE local_tasks SET status='failed',result=? WHERE id=?", (str(error)[:500],task_id))
                failed += 1
        return {'completed':completed,'failed':failed}

    def _execute(self, task_id, kind, payload):
        # Names are generated internally. No path supplied by model/user is used.
        directory = self.workspace / ('backups' if kind == 'backup' else 'inbox' if kind == 'reminder' else 'notes')
        if directory.is_symlink():
            raise ValueError('Diretório de saída não pode ser link simbólico')
        directory.mkdir(mode=0o700, exist_ok=True)
        target = directory / (task_id + ('.sqlite' if kind == 'backup' else '.txt'))
        if target.is_symlink():
            raise ValueError('Saída não pode ser link simbólico')
        if kind == 'backup':
            # Native SQLite snapshot includes committed memory even in WAL mode.
            source = sqlite3.connect(self.database, timeout=5)
            destination = sqlite3.connect(target)
            try:
                source.backup(destination)
                if destination.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                    raise RuntimeError('Backup falhou na verificação SQLite')
            finally:
                destination.close()
                source.close()
        else:
            target.write_text(payload['text']+'\n',encoding='utf-8')
        target.chmod(0o600)
        digest = hashlib.sha256()
        with target.open('rb') as file:
            for chunk in iter(lambda: file.read(1024*1024), b''):
                digest.update(chunk)
        notification = 'not_requested'
        if kind == 'reminder' and self.notifications:
            notification = 'inbox_only'
            if sys.platform == 'darwin':
                try:
                    subprocess.run(['/usr/bin/osascript', '-e',
                        'on run argv\ndisplay notification (item 1 of argv) with title "Athena"\nend run',
                        payload['text'][:500]], timeout=5, check=True, capture_output=True)
                    notification = 'submitted_to_macos'
                except (OSError, subprocess.SubprocessError):
                    notification = 'inbox_only'
        return {'path':str(target), 'sha256':digest.hexdigest(), 'kind':kind, 'notification':notification,
                'verified_at':datetime.now(timezone.utc).isoformat()}
