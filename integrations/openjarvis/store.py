"""Additive execution journal. A crash never silently replays a mutation."""
import json
import time
import uuid


class ExecutionStore:
    def __init__(self, tasks):
        self.tasks = tasks
        with tasks.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS agent_runs (
                id TEXT PRIMARY KEY, request TEXT NOT NULL, status TEXT NOT NULL,
                created REAL NOT NULL, updated REAL NOT NULL, response TEXT, metadata TEXT)''')
            db.execute('''CREATE TABLE IF NOT EXISTS agent_steps (
                id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, tool TEXT NOT NULL,
                arguments TEXT NOT NULL, status TEXT NOT NULL, result TEXT, created REAL NOT NULL)''')
            db.execute("UPDATE agent_runs SET status='interrupted',updated=? WHERE status='running'", (time.time(),))
            db.execute("UPDATE agent_steps SET status='uncertain' WHERE status='running'")

    def begin(self, request):
        run_id = uuid.uuid4().hex
        with self.tasks.connect() as db:
            db.execute('INSERT INTO agent_runs VALUES (?,?,?,?,?,?,?)',
                       (run_id, request, 'running', time.time(), time.time(), None, '{}'))
        return run_id

    def step(self, run_id, name, arguments):
        with self.tasks.connect() as db:
            row = db.execute('INSERT INTO agent_steps(run_id,tool,arguments,status,created) VALUES (?,?,?,?,?)',
                             (run_id, name, json.dumps(arguments, ensure_ascii=False), 'running', time.time()))
            return row.lastrowid

    def result(self, step_id, result):
        with self.tasks.connect() as db:
            db.execute('UPDATE agent_steps SET status=?,result=? WHERE id=?',
                       ('uncertain' if result.get('uncertain') else 'succeeded' if result['ok'] else 'failed', json.dumps(result, ensure_ascii=False), step_id))

    def finish(self, run_id, status, response, metadata):
        with self.tasks.connect() as db:
            db.execute('UPDATE agent_runs SET status=?,updated=?,response=?,metadata=? WHERE id=?',
                       (status, time.time(), response, json.dumps(metadata, ensure_ascii=False), run_id))

    def recent(self):
        with self.tasks.connect() as db:
            return [dict(zip(('id','request','status','updated'), row)) for row in db.execute(
                'SELECT id,request,status,updated FROM agent_runs ORDER BY created DESC LIMIT 10').fetchall()]
