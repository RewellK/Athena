"""Athena tool declarations and dispatch, independent of model and agent loop."""
import json
import importlib.util
import sys
import time
from datetime import datetime
from dataclasses import dataclass

from .memory import PersonalMemory
from .workspace import Workspace


@dataclass(frozen=True)
class Definition:
    name: str
    description: str
    properties: dict
    required: tuple
    capability: str
    handler: object
    mutates: bool = False

    def schema(self):
        return {'type': 'function', 'function': {'name': self.name, 'description': self.description,
                'parameters': {'type': 'object', 'properties': self.properties, 'required': list(self.required), 'additionalProperties': False}}}


S = {'type': 'string', 'maxLength': 8000}


class Catalog:
    def __init__(self, core, store):
        self.core, self.store = core, store
        self.memory = PersonalMemory(core)
        self.workspace = Workspace(core.local_tasks.workspace)
        self.definitions = {}
        self.add('create_note','Criar e verificar nota local.', {'text':S}, ('text',),'file:write',lambda a:self.task('note',a),True)
        self.add('backup_memory','Criar e verificar backup SQLite.',{},(),'file:write',lambda a:self.task('backup',a),True)
        self.add('remember','Guardar ou corrigir fato explícito: subject pessoa, attribute propriedade estável, fact valor.',{'subject':S,'attribute':S,'fact':S},('subject','attribute','fact'),'memory:write',lambda a:self.memory.remember(**a),True)
        self.add('recall','Buscar fatos persistentes e identidade do usuário.',{'subject':S},('subject',),'memory:read',lambda a:self.memory.search(a['subject']))
        self.add('memory_history','Consultar versões e correções de um fato.',{'subject':S},('subject',),'memory:read',lambda a:self.memory.history(a['subject']))
        self.add('schedule_reminder','Agendar lembrete. when deve ser ISO com fuso. Pergunte se faltar horário.',{'text':S,'when':S},('text','when'),'schedule:create',lambda a:self.task('reminder',a),True)
        self.add('list_tasks','Consultar tarefas reais, estados e resultados.',{},(),'memory:read',lambda a:{'tasks':core.local_tasks.list()})
        self.add('cancel_task','Cancelar tarefa pendente pelo ID.',{'task_id':S},('task_id',),'schedule:create',lambda a:{'cancelled':core.local_tasks.cancel(a['task_id'])},True)
        self.add('documents','Arquivos na pasta privada da Athena. operation=list|read|write. write exige name e content; não sobrescreve.',{'operation':{'type':'string','enum':['list','read','write']},'name':S,'content':S},('operation',),'workspace',self.documents)
        self.add('execution_history','Consultar execuções anteriores e tarefas interrompidas.',{},(),'memory:read',lambda a:{'runs':store.recent()})
        self.add('skills','Habilidades verificadas: operation=list|run|save|evolve|rollback. save exige name,run_id. run aceita overrides_json [{step,arguments}] para adaptar valores, com novo teste. evolve exige skill_id,program_json [{tool,arguments}].',{'operation':{'type':'string','enum':['list','run','save','evolve','rollback']},'name':S,'run_id':S,'skill_id':S,'program_json':S,'overrides_json':S},('operation',),'skills',self.skills)
        from .skills import ProcedureLibrary
        self.procedures = ProcedureLibrary(self)
        from .routines import Routines
        self.routines=Routines(self)
        from .goals import Goals
        self.goals=Goals(core.local_tasks)
        self.add('evolve_skill','Criar versão testada de habilidade ou reverter. operation=propose|rollback. propose exige program_json com lista [{tool,arguments}].',
            {'operation':{'type':'string','enum':['propose','rollback']},'skill_id':S,'program_json':S},('operation','skill_id'),'skills',self.evolve,True)
        from .learning_lab import LearningLab
        self.learning_lab=LearningLab(core.local_tasks)
        self.add('learning_status','Consultar preparação de dados de treino. Não treina pesos nem substitui modelos.',{},(),'memory:read',lambda a:self.learning_lab.status())
        from .computer import Computer
        computer=Computer(core.settings)
        if core.settings.get('computerToolsEnabled',False) and sys.platform=='darwin':
            self.add('open_app','Abrir aplicativo permitido: calculator, calendar, notes, textedit, safari, reminders.',{'name':S},('name',),'computer',computer.app,True)
            self.add('open_browser','Abrir URL no navegador padrão. Não confirma conteúdo renderizado.',{'url':S},('url',),'computer',computer.browser,True)
            self.add('calendar','Calendário macOS: operation=list|create. create exige calendar, title, start, end em ISO com fuso. Pode exigir permissão do macOS.',
                {'operation':{'type':'string','enum':['list','create']},'calendar':S,'title':S,'start':S,'end':S,'description':S},('operation',),'computer',computer.calendar,True)
        if core.settings.get('allowExternalRequests',False):
            from .web import read_public,search_public
            if importlib.util.find_spec('ddgs') is not None:
                self.add('web_search','Pesquisar fontes públicas na web, sem API paga. Retorna títulos, URLs e trechos.',{'query':S},('query',),'network:fetch',lambda a:search_public(a['query'],core.settings))
            self.add('read_web','Ler documento em URL HTTPS pública conhecida, com origem. Não faz busca geral nem navega em contas autenticadas.',{'url':S},('url',),'network:fetch',lambda a:read_public(a['url'],core.settings))

        self.add('memory','Memória: operation=remember|recall|history. remember exige subject (pessoa), attribute (ex: cor favorita) e fact (valor); use mesmo atributo ao corrigir. Só por pedido explícito.',
            {'operation':{'type':'string','enum':['remember','recall','history']},'subject':S,'attribute':S,'fact':S},('operation','subject'),'memory',self.memory_action)
        self.add('tasks','backup cria cópia SQLite completa, sem consultar memory. note copia trecho literal do pedido em text, sem aspas delimitadoras; para conteúdo novo use files write. operation=note|backup|reminder|list|cancel|history|schedule_skill|routines|cancel_routine|queue_goal|goals|cancel_goal. queue_goal exige request, when é opcional ISO com fuso; executa depois no residente local. schedule_skill exige skill_id e interval_seconds (mínimo 60). note exige text; reminder exige text e when ISO com fuso; cancel exige task_id.',
            {'operation':{'type':'string','enum':['note','backup','reminder','list','cancel','history','schedule_skill','routines','cancel_routine','queue_goal','goals','cancel_goal']},'text':S,'when':S,'task_id':S,'skill_id':S,'interval_seconds':S,'routine_id':S,'request':S,'goal_id':S},('operation',),'tasks',self.task_action)
        from .files import Files
        self.files=Files(core.settings,core.local_tasks.workspace)
        self.add('files','Arquivos em raízes autorizadas: operation=roots|list|read|mkdir|write|copy. root é alias; path relativo. write exige content; copy destination. Nunca sobrescreve.',
            {'operation':{'type':'string','enum':['roots','list','read','mkdir','write','copy']},'root':S,'path':S,'content':S,'destination':S},('operation',),'files',self.files.execute)
        self.add('queue_goal','Enfileirar objetivo local completo e autossuficiente, com dados e caminhos. when opcional ISO com fuso.',{'request':S,'when':S},('request',),'schedule:create',lambda a:self.task_action({'operation':'queue_goal',**a}),True)
        self.add('list_goals','Consultar objetivos na fila e seus resultados.',{},(),'memory:read',lambda a:{'goals':self.goals.list()})
        self.add('schedule_routine','Executar habilidade verificada periodicamente; intervalo mínimo 60 segundos.',{'skill_id':S,'interval_seconds':S},('skill_id','interval_seconds'),'schedule:create',lambda a:self.task_action({'operation':'schedule_skill',**a}),True)
        self.add('list_routines','Consultar rotinas recorrentes.',{},(),'memory:read',lambda a:{'routines':self.routines.list()})
        self.add('cancel_goal','Cancelar objetivo pendente pelo goal_id.',{'goal_id':S},('goal_id',),'schedule:create',lambda a:self.goals.cancel(a['goal_id']),True)
        self.add('cancel_routine','Cancelar rotina recorrente pelo routine_id.',{'routine_id':S},('routine_id',),'schedule:create',lambda a:self.routines.cancel(a['routine_id']),True)
        leaf_names={'create_note','backup_memory','remember','recall','memory_history','schedule_reminder','list_tasks','cancel_task','queue_goal','list_goals','schedule_routine','list_routines','cancel_goal','cancel_routine'}
        self.add('self_status','Consultar identidade, ferramentas reais, estado operacional e limites da própria Athena.',{},(),'memory:read',lambda a:self.self_status())
        leaf_names.add('self_status')
        self.public_names={'memory','tasks','files','skills'}|leaf_names
        self.discovery_names={'files','skills'}|leaf_names
        if core.settings.get('computerToolsEnabled',False) and sys.platform=='darwin':
            self.add('computer','macOS: operation=app|browser|calendars|event. app exige name; browser url; event calendar,title,start,end ISO com fuso.',
                {'operation':{'type':'string','enum':['app','browser','calendars','event']},'name':S,'url':S,'calendar':S,'title':S,'start':S,'end':S},('operation',),'computer',self.computer_action,True)
            self.public_names.add('computer')
            self.discovery_names.add('computer')
        if core.settings.get('allowExternalRequests',False):
            self.public_names.add('read_web');self.discovery_names.add('read_web')
            if 'web_search' in self.definitions:
                self.public_names.add('web_search');self.discovery_names.add('web_search')
        self.browser=None
        if core.settings.get('browserToolsEnabled',False) and importlib.util.find_spec('playwright') is not None:
            from .browser import Browser
            self.browser=Browser(core.settings)
            self.add('browser','Navegador isolado: operation=navigate|inspect|click|fill. navigate exige url; click exige target (ID retornado); fill exige target e text, se habilitado.',
                {'operation':{'type':'string','enum':['navigate','inspect','click','fill']},'url':S,'target':S,'text':S},('operation',),'browser',self.browser.execute)
            self.public_names.add('browser')
            self.discovery_names.add('browser')

    def add(self, name, description, properties, required, capability, handler, mutates=False):
        self.definitions[name] = Definition(name, description, properties, required, capability, handler, mutates)

    def validate(self, name, arguments):
        definition = self.definitions.get(name)
        if not definition or not isinstance(arguments,dict):
            raise ValueError('Ferramenta ou argumentos inválidos')
        if set(arguments)-set(definition.properties) or set(definition.required)-set(arguments):
            raise ValueError('Campos inválidos ou ausentes. Obrigatórios: '+str(definition.required)+'; permitidos: '+str(list(definition.properties)))
        for field,value in arguments.items():
            schema = definition.properties[field]
            if not isinstance(value,str) or not value.strip() or len(value)>schema.get('maxLength',8000) or ('enum' in schema and value not in schema['enum']):
                raise ValueError('Valor inválido para '+field+'; opções: '+str(schema.get('enum','texto não vazio até 8000 caracteres')))
        return definition

    def is_write(self, name, args):
        return (name=='files' and args.get('operation') in {'mkdir','write','copy'}) or (name=='browser' and args.get('operation') in {'click','fill'}) or (name=='memory' and args.get('operation')=='remember') or (name=='tasks' and args.get('operation') in {'note','backup','reminder','cancel','schedule_skill','cancel_routine','queue_goal','cancel_goal'}) or self.definitions[name].mutates or (name=='documents' and args.get('operation')=='write') or (name=='skills' and args.get('operation')!='list')

    def execute(self, name, arguments):
        definition = self.validate(name, arguments)
        if self.is_write(name, arguments) and not self.core.settings.get('localAutonomyEnabled',True):
            raise ValueError('Autonomia local desativada')
        return definition.handler(arguments)

    def task(self, kind, args):
        due = None
        if kind=='reminder':
            when = datetime.fromisoformat(args['when'])
            if not when.tzinfo:
                raise ValueError('Horário precisa incluir fuso')
            due = when.timestamp()
        text=self.note_text(args.get('text','')) if kind=='note' else args.get('text','')
        task_id = self.core.local_tasks.schedule(kind,text,due)
        self.core.local_tasks.run_once()
        task = next(t for t in self.core.local_tasks.list() if t['id']==task_id)
        if task['status']=='failed':
            raise RuntimeError(task['result'])
        if task['status']=='completed':
            task['result']=json.loads(task['result'])
        return task

    @staticmethod
    def note_text(text):
        # A JSON string encoded inside a string is a transport wrapper, not
        # natural-language intent. Plain notes unbox it; files.write stays raw.
        if isinstance(text,str):
            try:
                decoded=json.loads(text)
                if isinstance(decoded,str):
                    return decoded
            except (ValueError,TypeError):
                pass
        return text

    def documents(self, args):
        op = args['operation']
        if op=='list': return self.workspace.list()
        if 'name' not in args: raise ValueError('Nome do documento é necessário')
        if op=='read': return self.workspace.read(args['name'])
        if 'content' not in args: raise ValueError('Conteúdo é necessário')
        return self.workspace.write(args['name'],args['content'])

    def skills(self, args):
        op=args['operation']
        if op=='list': return {'skills':self.procedures.list(), 'legacy':self.core.skill_backend.list()}
        if op=='save': return self.procedures.save(args['name'],args['run_id'])
        if op=='evolve': return self.procedures.evolve(args['skill_id'],args['program_json'])
        if op=='rollback': return self.procedures.rollback(args['skill_id'])
        return self.procedures.run(args['skill_id'],args.get('overrides_json'))

    def evolve(self,args):
        if args['operation']=='rollback': return self.procedures.rollback(args['skill_id'])
        if 'program_json' not in args: raise ValueError('program_json é necessário')
        return self.procedures.evolve(args['skill_id'],args['program_json'])

    def memory_action(self,args):
        op=args['operation']
        if op=='remember':
            if 'fact' not in args or 'attribute' not in args: raise ValueError('remember exige subject, attribute (nome estável da propriedade) e fact (valor)')
            return self.memory.remember(args['subject'],args['fact'],args['attribute'])
        if op=='history': return self.memory.history(args['subject'])
        return self.memory.search(args['subject'])

    def task_action(self,args):
        op=args['operation']
        if self.core.settings.get('executingQueuedGoal',False) and op in {'queue_goal','schedule_skill'}:
            raise ValueError('Objetivo em segundo plano não cria novos objetivos ou rotinas recorrentes')
        if op=='queue_goal': return self.goals.schedule(args['request'],args.get('when'))
        if op=='goals': return {'goals':self.goals.list()}
        if op=='cancel_goal': return self.goals.cancel(args['goal_id'])
        if op=='schedule_skill': return self.routines.schedule(args['skill_id'],args['interval_seconds'])
        if op=='routines': return {'routines':self.routines.list()}
        if op=='cancel_routine': return self.routines.cancel(args['routine_id'])
        if op=='list': return {'tasks':self.core.local_tasks.list()}
        if op=='history': return {'runs':self.store.recent()}
        if op=='cancel': return {'cancelled':self.core.local_tasks.cancel(args['task_id'])}
        if op in {'note','reminder'} and 'text' not in args: raise ValueError('text é necessário')
        if op=='reminder' and 'when' not in args: raise ValueError('when é necessário')
        return self.task(op,args)

    def computer_action(self,args):
        from .computer import Computer
        computer=Computer(self.core.settings)
        op=args['operation']
        if op=='app': return computer.app({'name':args['name']})
        if op=='browser': return computer.browser({'url':args['url']})
        return computer.calendar({**args,'operation':'list' if op=='calendars' else 'create'})

    def self_status(self):
        supervisor=getattr(self.core,'runtime_supervisor',None)
        return {'identity':self.core.identity,'backend':'OpenJarvis OrchestratorAgent',
            'model':self.core.settings.get('ollamaModel'),
            'tools':[{'name':name,'description':self.definitions[name].description} for name in sorted(self.discovery_names)],
            'runtime':supervisor.get_status() if supervisor else {'state':'test'},
            'learned_procedures':self.procedures.list(),
            'training':self.learning_lab.status(),
            'limits':['No unrestricted generated code installation','No automatic weight training or replacement',
                      'Computer apps and microphone require macOS permissions','Only authorized file roots',
                      'External accounts are not connected by this runtime']}
