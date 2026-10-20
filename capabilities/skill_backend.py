"""Learn executable local recipes by composing tested, bounded tools."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import uuid

from agency.local_tasks import LocalTasks


class SkillBackend:
    def __init__(self, tasks, llm_provider=None):
        self.tasks, self.llm_provider = tasks, llm_provider
        with tasks.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS local_skills (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, program TEXT NOT NULL,
                digest TEXT NOT NULL, status TEXT NOT NULL, verification TEXT,
                created REAL NOT NULL)''')
            columns={row[1] for row in db.execute('PRAGMA table_info(local_skills)')}
            if 'activation_origin' not in columns:
                db.execute('ALTER TABLE local_skills ADD COLUMN activation_origin TEXT')

    def validate(self, program):
        if not isinstance(program,dict) or set(program) != {'name','steps'}:
            raise ValueError('Habilidade deve ter name e steps')
        if not isinstance(program['name'],str) or not 1 <= len(program['name']) <= 120:
            raise ValueError('Nome inválido')
        steps=program['steps']
        if not isinstance(steps,list) or not 1 <= len(steps) <= 5:
            raise ValueError('Habilidade deve conter de 1 a 5 passos')
        for step in steps:
            if not isinstance(step,dict) or not set(step) <= {'kind','text'} or step.get('kind') not in LocalTasks.KINDS:
                raise ValueError('Falta ferramenta implementada: permitido apenas note, reminder, backup')
            text=step.get('text','')
            if not isinstance(text,str) or len(text)>8000 or (step['kind']!='backup' and not text.strip()):
                raise ValueError('Passo exige texto válido')
        return hashlib.sha256(json.dumps(program,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def propose(self, program):
        digest=self.validate(program)
        skill_id=uuid.uuid4().hex
        with self.tasks.connect() as db:
            existing=db.execute('SELECT id FROM local_skills WHERE digest=?',(digest,)).fetchone()
            if existing: return self.get(existing[0])
            db.execute('INSERT INTO local_skills(id,name,program,digest,status,created) VALUES (?,?,?,?,?,?)',
                (skill_id,program['name'],json.dumps(program,ensure_ascii=False),digest,'candidate',time.time()))
        return self.get(skill_id)

    def get(self, skill_id):
        with self.tasks.connect() as db:
            row=db.execute('SELECT id,name,program,digest,status,verification,activation_origin FROM local_skills WHERE id=?',(skill_id,)).fetchone()
        if not row: raise ValueError('Habilidade não encontrada')
        return dict(zip(('id','name','program','digest','status','verification','activation_origin'),row))

    def list(self):
        with self.tasks.connect() as db:
            return [self.get(row[0]) for row in db.execute('SELECT id FROM local_skills ORDER BY created DESC LIMIT 100').fetchall()]

    def verify(self, skill_id):
        skill=self.get(skill_id); program=json.loads(skill['program']); self.validate(program)
        # Execute all steps in a temporary workspace with an independent empty DB.
        with tempfile.TemporaryDirectory(prefix='athena-skill-test-') as root:
            tasks=LocalTasks(str(Path(root)/'test.sqlite'),Path(root)/'workspace')
            for step in program['steps']: tasks.schedule(step['kind'],step.get('text',''))
            result=tasks.run_once()
            passed=result['failed']==0 and result['completed']==len(program['steps'])
            report={'passed':passed,'steps':len(program['steps']),'executed':result['completed'],'isolated':True}
        with self.tasks.connect() as db:
            db.execute('UPDATE local_skills SET verification=? WHERE id=?',(json.dumps(report),skill_id))
        return report

    def activate(self, skill_id, approval, activation_origin="user_review"):
        skill=self.get(skill_id)
        if approval!=skill['digest']: raise ValueError('Aprovação deve ser o hash exato da habilidade revisada')
        if not self.verify(skill_id)['passed']: raise ValueError('Habilidade falhou na verificação')
        with self.tasks.connect() as db:
            db.execute("UPDATE local_skills SET status='active',activation_origin=? WHERE id=?",(activation_origin,skill_id))
        return self.get(skill_id)

    def run(self, skill_id):
        skill=self.get(skill_id)
        if skill['status']!='active': raise ValueError('Habilidade ainda não foi aprovada')
        program=json.loads(skill['program'])
        if self.validate(program)!=skill['digest']: raise ValueError('Habilidade foi alterada após aprovação')
        scheduled=[self.tasks.schedule(step['kind'],step.get('text','')) for step in program['steps']]
        execution=self.tasks.run_once()
        return {'scheduled':scheduled,'execution':execution,
                'tasks':[item for item in self.tasks.list() if item['id'] in scheduled]}

    def learn(self, request, allow_local_policy=False):
        result=self.design(request)
        if result.get('status')!='awaiting_review' or not allow_local_policy:
            return result
        skill=result['skill']
        # Authority comes from the Core's configured allowlist, never from LLM text.
        active=self.activate(skill['id'],skill['digest'],activation_origin='verified_local_composition_policy')
        return {'status':'active','skill':active,'verification':result['verification']}

    def design(self, request):
        if not self.llm_provider: return {'status':'unavailable','reason':'LLM auxiliar indisponível para projeto novo'}
        prompt='''Projete uma habilidade local como receita JSON com name e steps.
Ferramentas reais: note(text), reminder(text), backup(). Até 5 passos.
Não há shell, rede, e-mail ou criação de conectores. Se precisar dessas ferramentas, retorne {"missing_tool":"descrição"}.
Cada passo é {"kind":"note|reminder|backup","text":"conteúdo"}.
A receita não agenda horários: lembretes da receita são para a caixa local imediata.
Não execute nem aprove nada. Pedido do usuário:\n'''+str(request)
        result=self.llm_provider.generate(prompt,response_format='json')
        if not result.available: return {'status':'unavailable','reason':result.error}
        try:
            program=json.loads(result.text)
            if program.get('missing_tool'):
                return {'status':'missing_tool','reason':str(program['missing_tool'])[:1000]}
            skill=self.propose(program)
            report=self.verify(skill['id'])
            return {'status':'awaiting_review','skill':self.get(skill['id']),'verification':report}
        except (ValueError,TypeError,AttributeError) as error:
            return {'status':'invalid_proposal','reason':str(error)}
