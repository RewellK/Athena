"""Durable user-requested background objectives with bounded local execution."""
from datetime import datetime
import time
import uuid


class Goals:
    def __init__(self,tasks):
        self.tasks=tasks
        with tasks.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS queued_goals (
                id TEXT PRIMARY KEY, request TEXT NOT NULL, due REAL NOT NULL,
                status TEXT NOT NULL, result TEXT, created REAL NOT NULL)''')
            db.execute("UPDATE queued_goals SET status='interrupted' WHERE status='running'")

    def schedule(self,request,when=None):
        if not request.strip() or len(request)>8000: raise ValueError('Objetivo inválido')
        due=time.time()
        if when:
            parsed=datetime.fromisoformat(when)
            if not parsed.tzinfo: raise ValueError('Data precisa incluir fuso')
            due=parsed.timestamp()
        if not time.time()-60<=due<=time.time()+366*86400: raise ValueError('Data fora do intervalo de um ano')
        goal_id=uuid.uuid4().hex
        with self.tasks.connect() as db:
            if db.execute("SELECT count(*) FROM queued_goals WHERE status='pending'").fetchone()[0]>=20:
                raise ValueError('Limite de 20 objetivos pendentes')
            db.execute('INSERT INTO queued_goals VALUES (?,?,?,?,?,?)',(goal_id,request,due,'pending',None,time.time()))
        return {'goal_id':goal_id,'status':'queued','due':due,'requires':'resident running; local model available'}

    def list(self):
        with self.tasks.connect() as db:
            return [dict(zip(('id','request','due','status','result'),r)) for r in db.execute('SELECT id,request,due,status,result FROM queued_goals ORDER BY created DESC LIMIT 50').fetchall()]

    def cancel(self,goal_id):
        with self.tasks.connect() as db:
            changed=db.execute("UPDATE queued_goals SET status='cancelled' WHERE id=? AND status='pending'",(goal_id,)).rowcount
        return {'cancelled':bool(changed)}

    def tick(self,core):
        if not core.settings.get('residentGoalsEnabled',False) or not core.settings.get('localAutonomyEnabled',True):
            return {'executed':0}
        if not core.settings.get('queuedGoalModelEnabled',core.settings.get('useLLM',True)):
            return {'executed':0}
        with self.tasks.connect() as db:
            goal=db.execute("SELECT id,request FROM queued_goals WHERE status='pending' AND due<=? ORDER BY due LIMIT 1",(time.time(),)).fetchone()
            if not goal: return {'executed':0}
            if not db.execute("UPDATE queued_goals SET status='running' WHERE id=? AND status='pending'",(goal[0],)).rowcount:
                return {'executed':0}
        previous=core.settings.get('useLLM',True)
        previous_background=core.settings.get('executingQueuedGoal',False)
        previous_context=getattr(core,'conversation_context',None)
        try:
            # Only this explicitly queued goal may invoke local inference.
            # Resident disables browser, computer control, external requests and
            # teachers before constructing its runtime/tool catalog.
            core.settings.values['useLLM']=True
            core.settings.values['executingQueuedGoal']=True
            core.last_response_metadata={}
            if previous_context is not None:
                from conversation.conversation_context import ConversationContext
                core.conversation_context=ConversationContext()
            response=core.chat(goal[1])
            run_status=core.last_response_metadata.get('status')
            status='answered' if run_status=='finished' else 'needs_attention'
            if core.last_response_metadata.get('cancelled') and core.last_response_metadata.get('cancel_reason') in {'foreground_handoff','shutdown','pause'} and not core.last_response_metadata.get('tools_executed'):
                status='pending'
        except Exception as error:
            response='Objetivo interrompido: '+str(error)[:500];status='needs_attention'
        finally:
            core.settings.values['useLLM']=previous
            core.settings.values['executingQueuedGoal']=previous_background
            if previous_context is not None:
                core.conversation_context=previous_context
        with self.tasks.connect() as db:
            db.execute('UPDATE queued_goals SET status=?,result=? WHERE id=?',(status,response,goal[0]))
        if status=='pending':
            return {'executed':0,'goal_id':goal[0],'status':'waiting_for_idle'}
        # Always leave a result the user can inspect without an active GUI.
        self.tasks.schedule('reminder',f'Objetivo {goal[0]} — {status}\n{response}'[:8000])
        self.tasks.run_once()
        return {'executed':1,'goal_id':goal[0],'status':status}
