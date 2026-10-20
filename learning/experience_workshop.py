"""Learning backlog: real failures, proposed changes, tested procedure evolution."""
import json
from pathlib import Path
import time
import uuid
from llm.provider import OllamaProvider


class ExperienceWorkshop:
    def __init__(self,core):
        self.core=core;self.tasks=core.local_tasks
        with self.tasks.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS learning_issues (
                category TEXT NOT NULL, reference TEXT NOT NULL, detail TEXT NOT NULL,
                created REAL NOT NULL, UNIQUE(category,reference))''')
            db.execute('CREATE TABLE IF NOT EXISTS workshop_state (key TEXT PRIMARY KEY,value REAL NOT NULL)')
            db.execute('''CREATE TABLE IF NOT EXISTS improvement_proposals (
                id TEXT PRIMARY KEY,body TEXT NOT NULL,status TEXT NOT NULL,
                validation TEXT,created REAL NOT NULL,applied REAL)''')
    def observe(self,category,reference,detail):
        with self.tasks.connect() as db:
            db.execute('INSERT OR IGNORE INTO learning_issues VALUES (?,?,?,?)',(category,reference,str(detail)[:500],time.time()))
    def collect(self):
        with self.tasks.connect() as db:
            columns={r[1] for r in db.execute("PRAGMA table_info(agent_runs)")}
            if columns:
                for run_id,status,metadata in db.execute('SELECT id,status,metadata FROM agent_runs ORDER BY created DESC LIMIT 100').fetchall():
                    info=json.loads(metadata or '{}')
                    if status in ('partial','failed','finished_with_errors'):
                        self.observe('execution_difficulty',run_id,status)
                    if info.get('duration_ms',0)>30000:
                        self.observe('slow_response',run_id,str(round(info['duration_ms']/1000,1))+' segundos')
        return self.report()
    def report(self):
        with self.tasks.connect() as db:
            issues=[{'category':r[0],'count':r[1],'last_seen':r[2]} for r in db.execute('SELECT category,count(*),max(created) FROM learning_issues GROUP BY category ORDER BY count(*) DESC')]
            proposals=[{'id':r[0],'body':json.loads(r[1]),'status':r[2],'validation':json.loads(r[3]) if r[3] else None} for r in db.execute('SELECT id,body,status,validation FROM improvement_proposals ORDER BY created DESC LIMIT 10')]
        return {'issues':issues,'proposals':proposals}
    def tick(self):
        report=self.collect()
        if not self.core.settings.get('autoExperienceReview',True):return report
        with self.tasks.connect() as db:
            previous=db.execute("SELECT value FROM workshop_state WHERE key='last_notice'").fetchone()
            pending=db.execute("SELECT count(*) FROM improvement_proposals WHERE status IN ('proposed','tested')").fetchone()[0]
        if pending or not report['issues'] or sum(i['count'] for i in report['issues'])<3:return report
        if previous and time.time()-previous[0]<86400:return report
        issue=report['issues'][0]
        body={'problem':str(issue['count'])+' experiências de '+issue['category'],
              'why':'Este padrão apareceu em execuções reais. A causa ainda precisa ser investigada.',
              'change':'Investigar as execuções deste grupo, comparar uma correção em cópia separada e conservar um teste que reproduza a falha.',
              'kind':'code','skill_id':'','program_json':''}
        proposal=self.save_proposal(body)
        self.tasks.schedule('reminder','Chefe, notei uma dificuldade recorrente e preparei uma proposta na aba Aprender: '+body['problem'])
        with self.tasks.connect() as db:db.execute("INSERT OR REPLACE INTO workshop_state VALUES ('last_notice',?)",(time.time(),))
        voice=getattr(self.core,'voice_engine',None)
        if voice:voice.speak('Chefe, notei uma dificuldade recorrente. Preparei uma proposta na aba Aprender.')
        return proposal

    def propose(self):
        report=self.collect();procedures=self.core.agent_runtime.catalog.procedures
        skills=[]
        for entry in procedures.list()[:4]:
            skill=procedures.get(entry['id'])
            skills.append({'id':entry['id'],'name':skill['name'],'program':skill['program']})
        if not report['issues'] and not skills:return {'status':'no_evidence','message':'Ainda não tenho experiências suficientes para propor uma melhoria concreta.'}
        schema={'type':'object','properties':{
            'problem':{'type':'string'},'why':{'type':'string'},'change':{'type':'string'},
            'kind':{'type':'string','enum':['procedure','code','configuration','knowledge']},
            'skill_id':{'type':'string'},'program_json':{'type':'string'}},
            'required':['problem','why','change','kind','skill_id','program_json'],'additionalProperties':False}
        payload={'issues':report['issues'],'skills':skills,'allowed_procedure_tools':sorted(procedures.ALLOWED)}
        provider=OllamaProvider(self.core.settings,getattr(self.core,'logger',None))
        result=provider.generate('',messages=[{'role':'system','content':
            'Você revisa experiências reais da Athena. Proponha UMA melhoria e explique por quê. Não invente falhas ou sucesso. '
            'Para melhorar procedimento existente, kind=procedure, skill_id existente e program_json com lista completa [{tool,arguments}]; '
            'use apenas ferramentas permitidas e preserve o objetivo. Para mudança de código ou configuração, descreva uma proposta investigável, '
            'sem fingir que está pronta. Campos não usados devem ser strings vazias. Só JSON.'},
            {'role':'user','content':json.dumps(payload,ensure_ascii=False)}],response_format=schema)
        if not result.available:raise ValueError(result.error or 'Modelo local indisponível')
        return self.save_proposal(json.loads(result.text))
    def save_proposal(self,body):
        required=('problem','why','change','kind','skill_id','program_json')
        if any(not isinstance(body.get(k),str) for k in required):raise ValueError('Proposta inválida')
        validation=None;status='proposed'
        if body['kind']=='procedure':
            library=self.core.agent_runtime.catalog.procedures
            library.get(body['skill_id'])
            program=library.validate(json.loads(body['program_json']))
            validation=library.verify(program)
            status='tested' if validation.get('passed') else 'test_failed'
        proposal_id=uuid.uuid4().hex
        with self.tasks.connect() as db:db.execute('INSERT INTO improvement_proposals VALUES (?,?,?,?,?,NULL)',(proposal_id,json.dumps(body,ensure_ascii=False),status,json.dumps(validation) if validation else None,time.time()))
        return {'id':proposal_id,'body':body,'status':status,'validation':validation}
    def approve(self,proposal_id):
        with self.tasks.connect() as db:row=db.execute('SELECT body,status FROM improvement_proposals WHERE id=?',(proposal_id,)).fetchone()
        if not row:raise ValueError('Proposta não encontrada')
        body=json.loads(row[0])
        if row[1]=='applied':raise ValueError('Proposta já aplicada')
        if body['kind']!='procedure' or row[1]!='tested':
            return self.export(proposal_id)
        result=self.core.agent_runtime.catalog.procedures.evolve(body['skill_id'],body['program_json'])
        with self.tasks.connect() as db:db.execute("UPDATE improvement_proposals SET status='applied',applied=? WHERE id=?",(time.time(),proposal_id))
        return {'applied':True,'result':result,'rollback':'Reverter pela ferramenta skills com o ID da nova variante.'}
    def export(self,proposal_id):
        with self.tasks.connect() as db:row=db.execute('SELECT body FROM improvement_proposals WHERE id=?',(proposal_id,)).fetchone()
        if not row:raise ValueError('Proposta não encontrada')
        body=json.loads(row[0]);directory=self.tasks.workspace/'improvements';directory.mkdir(exist_ok=True,mode=0o700)
        path=directory/(proposal_id+'.md')
        text='# Proposta de melhoria da Athena\n\n'+body['problem']+'\n\nPor quê: '+body['why']+'\n\nMudança proposta: '+body['change']+'\n\nTrabalhar em cópia separada. Comparar testes antes/depois e documentar reversão. Não publicar dados pessoais nem modificar a instalação ativa.\n'
        path.write_text(text);path.chmod(0o600)
        return {'exported':str(path),'applied':False,'reason':'Mudança de código/configuração exige implementação e testes específicos; exportação não é execução.'}
