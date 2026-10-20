"""Persistent opt-in routines made from already verified procedures."""
import json
import time
import uuid


class Routines:
    def __init__(self,catalog):
        self.catalog=catalog
        self.tasks=catalog.core.local_tasks
        with self.tasks.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS agent_routines (
                id TEXT PRIMARY KEY, skill_id TEXT NOT NULL, interval REAL NOT NULL,
                next_due REAL NOT NULL, status TEXT NOT NULL, result TEXT, updated REAL NOT NULL)''')
            # Unknown side effects after crash require review, not automatic repetition.
            db.execute("UPDATE agent_routines SET status='interrupted' WHERE status='running'")

    def schedule(self,skill_id,interval_seconds):
        skill=self.catalog.procedures.get(skill_id)
        if skill['status']!='active': raise ValueError('Habilidade precisa estar ativa')
        interval=float(interval_seconds)
        if not 60<=interval<=30*86400: raise ValueError('Intervalo deve ser de 60 segundos a 30 dias')
        routine_id=uuid.uuid4().hex
        with self.tasks.connect() as db:
            db.execute('INSERT INTO agent_routines VALUES (?,?,?,?,?,?,?)',
                       (routine_id,skill_id,interval,time.time()+interval,'pending',None,time.time()))
        return {'routine_id':routine_id,'status':'scheduled','interval_seconds':interval}

    def list(self):
        with self.tasks.connect() as db:
            rows=db.execute('SELECT id,skill_id,interval,next_due,status,result FROM agent_routines ORDER BY updated DESC LIMIT 50').fetchall()
        return [dict(zip(('id','skill_id','interval','next_due','status','result'),row)) for row in rows]

    def cancel(self,routine_id):
        with self.tasks.connect() as db:
            count=db.execute("UPDATE agent_routines SET status='cancelled',updated=? WHERE id=? AND status!='running'",(time.time(),routine_id)).rowcount
        return {'cancelled':bool(count)}

    def tick(self):
        if not self.catalog.core.settings.get('localAutonomyEnabled',True): return {'executed':0}
        with self.tasks.connect() as db:
            rows=db.execute("SELECT id,skill_id,interval FROM agent_routines WHERE status='pending' AND next_due<=? ORDER BY next_due LIMIT 1",(time.time(),)).fetchall()
        completed=0
        for routine_id,skill_id,interval in rows:
            with self.tasks.connect() as db:
                claimed=db.execute("UPDATE agent_routines SET status='running',updated=? WHERE id=? AND status='pending'",(time.time(),routine_id)).rowcount
            if not claimed: continue
            try:
                result=self.catalog.procedures.run(skill_id)
                status='pending';completed+=1
            except Exception as error:
                result={'error':str(error)[:500]};status='failed'
            with self.tasks.connect() as db:
                db.execute('UPDATE agent_routines SET status=?,next_due=?,result=?,updated=? WHERE id=?',
                           (status,time.time()+interval,json.dumps(result,ensure_ascii=False),time.time(),routine_id))
        return {'executed':completed}
