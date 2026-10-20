"""Acquire procedures from execution evidence; verify before reuse or evolution."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time
import uuid


class ProcedureLibrary:
    # Recipes contain only finite invocations of registered local tools.
    ALLOWED = {'create_note','backup_memory','documents','recall','tasks','files','memory'}

    def __init__(self, catalog):
        self.catalog = catalog
        self.tasks = catalog.core.local_tasks
        with self.tasks.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS procedures (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, program TEXT NOT NULL, digest TEXT NOT NULL,
                status TEXT NOT NULL, verification TEXT NOT NULL, source_run TEXT, parent TEXT, created REAL NOT NULL)''')

    @staticmethod
    def digest(program):
        return hashlib.sha256(json.dumps(program,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

    def validate(self, program):
        if not isinstance(program,list) or not 1<=len(program)<=8:
            raise ValueError('Procedimento deve ter de 1 a 8 etapas')
        for step in program:
            if not isinstance(step,dict) or set(step)!={'tool','arguments'} or step['tool'] not in self.ALLOWED:
                raise ValueError('Procedimento contém ferramenta não permitida')
            self.catalog.validate(step['tool'],step['arguments'])
            if step['tool']=='memory' and step['arguments'].get('operation') not in {'recall','history'}:
                raise ValueError('Procedimentos só podem consultar memória; gravação exige pedido atual explícito')
            if step['tool']=='files' and step['arguments'].get('root','workspace')!='workspace':
                raise ValueError('Aprendizado automático de arquivos fica limitado à raiz workspace')
            if step['tool']=='tasks' and step['arguments'].get('operation') not in {'note','backup','list'}:
                raise ValueError('Procedimentos só reutilizam notas, backup e consulta de tarefas')
        return program

    def verify(self, program):
        from agency.local_tasks import LocalTasks
        from capabilities.skill_backend import SkillBackend
        from memory.database import MemoryDB
        from .catalog import Catalog
        from .store import ExecutionStore
        self.validate(program)
        with tempfile.TemporaryDirectory(prefix='athena-procedure-') as root:
            tasks=LocalTasks(str(Path(root)/'memory.sqlite'),Path(root)/'workspace',notifications=False)
            memory=MemoryDB(tasks.database)
            core=SimpleNamespace(local_tasks=tasks,memory=memory,identity=self.catalog.core.identity,
                creator_name=self.catalog.core.creator_name,settings={'localAutonomyEnabled':True},
                skill_backend=SkillBackend(tasks))
            try:
                isolated=Catalog(core,ExecutionStore(tasks))
                results=[isolated.execute(step['tool'],step['arguments']) for step in program]
                return {'passed':True,'steps':len(results),'isolated':True,'verified_at':time.time()}
            finally:
                memory.close()

    def create(self,name,program,source_run=None,parent=None):
        if not isinstance(name,str) or not 1<=len(name)<=120:
            raise ValueError('Nome inválido')
        self.validate(program)
        report=self.verify(program)
        digest=self.digest(program)
        with self.tasks.connect() as db:
            old=db.execute('SELECT id FROM procedures WHERE digest=?',(digest,)).fetchone()
            if old: return self.get(old[0])
            skill_id=uuid.uuid4().hex
            active=self.catalog.core.settings.get('autonomousLocalSkillLearning',True)
            db.execute('INSERT INTO procedures VALUES (?,?,?,?,?,?,?,?,?)',
                (skill_id,name,json.dumps(program,ensure_ascii=False),digest,'active' if active else 'candidate',
                 json.dumps(report),source_run,parent,time.time()))
        return self.get(skill_id)

    def save(self,name,run_id):
        with self.tasks.connect() as db:
            run=db.execute('SELECT status FROM agent_runs WHERE id=?',(run_id,)).fetchone()
            rows=db.execute('SELECT tool,arguments,status FROM agent_steps WHERE run_id=? ORDER BY id',(run_id,)).fetchall()
        if not run or run[0] not in {'finished','finished_with_errors','executed'} or not rows or any(r[2] in {'running','uncertain'} for r in rows):
            raise ValueError('Aprendizado exige execução anterior concluída com ferramentas bem sucedidas')
        rows=[row for row in rows if row[2]=='succeeded']
        if not rows:
            raise ValueError('Nenhuma etapa bem sucedida para aprender')
        program=[]; seen=set()
        for tool,arguments,_ in rows:
            step={'tool':tool,'arguments':json.loads(arguments)}
            signature=json.dumps(step,sort_keys=True,ensure_ascii=False)
            if signature not in seen:
                seen.add(signature);program.append(step)
        return self.create(name,program,source_run=run_id)

    def get(self,skill_id):
        with self.tasks.connect() as db:
            row=db.execute('SELECT id,name,program,digest,status,verification,source_run,parent FROM procedures WHERE id=?',(skill_id,)).fetchone()
        if not row: raise ValueError('Habilidade não encontrada')
        item=dict(zip(('id','name','program','digest','status','verification','source_run','parent'),row))
        item['program']=json.loads(item['program']); item['verification']=json.loads(item['verification'])
        return item

    def list(self):
        with self.tasks.connect() as db:
            rows=db.execute('SELECT id,name,status,parent FROM procedures ORDER BY created DESC LIMIT 30').fetchall()
        return [dict(zip(('id','name','status','parent'),r)) for r in rows]

    def run(self,skill_id,overrides_json=None):
        skill=self.get(skill_id)
        if skill['status']!='active' or self.digest(skill['program'])!=skill['digest']:
            raise ValueError('Habilidade inativa ou alterada')
        program=skill['program']
        if overrides_json:
            overrides=json.loads(overrides_json)
            if not isinstance(overrides,list) or len(overrides)>8:
                raise ValueError('Adaptação deve ser lista de até oito alterações {step,arguments}')
            for change in overrides:
                if not isinstance(change,dict) or set(change)!={'step','arguments'} or type(change['step']) is not int or not 0<=change['step']<len(program) or not isinstance(change['arguments'],dict):
                    raise ValueError('Adaptação inválida')
                program[change['step']]['arguments'].update(change['arguments'])
            self.verify(program)
        self.validate(program)
        results=[]
        for step in program:
            results.append(self.catalog.execute(step['tool'],step['arguments']))
        return {'skill_id':skill_id,'completed':len(results),'results':results}

    def evolve(self,skill_id,changes_json):
        skill=self.get(skill_id)
        if len(changes_json)>16000: raise ValueError('Alteração muito grande')
        # Full finite recipe, validated by exactly the same schema and allowlist.
        program=json.loads(changes_json)
        candidate=self.create(skill['name'],program,source_run=skill['source_run'],parent=skill_id)
        if candidate['id']!=skill_id and candidate['status']=='active':
            with self.tasks.connect() as db:
                db.execute("UPDATE procedures SET status='retired' WHERE id=?",(skill_id,))
                db.execute('UPDATE agent_routines SET skill_id=? WHERE skill_id=? AND status=?',
                           (candidate['id'],skill_id,'pending'))
        candidate['comparison']={'baseline_passed':skill['verification']['passed'],
            'candidate_passed':candidate['verification']['passed'],
            'baseline_steps':len(skill['program']),'candidate_steps':len(program),
            'scope':'tool execution in isolated fixtures; semantic superiority is not proven'}
        return candidate

    def rollback(self,skill_id):
        skill=self.get(skill_id)
        if not skill['parent']: raise ValueError('Esta versão não possui antecessora')
        with self.tasks.connect() as db:
            db.execute("UPDATE procedures SET status='retired' WHERE id=?",(skill_id,))
            db.execute("UPDATE procedures SET status='active' WHERE id=?",(skill['parent'],))
            db.execute('UPDATE agent_routines SET skill_id=? WHERE skill_id=? AND status=?',
                       (skill['parent'],skill_id,'pending'))
        return self.get(skill['parent'])
