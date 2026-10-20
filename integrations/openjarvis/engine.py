"""Adapt Athena's bounded, loopback-only Ollama transport to OpenJarvis."""
import json
from openjarvis.engine._stubs import InferenceEngine


class ModelUnavailable(RuntimeError):
    pass


class AthenaOllamaEngine(InferenceEngine):
    engine_id = 'athena_ollama'
    is_cloud = False

    def __init__(self, provider):
        self.provider = provider
        self.calls = 0
        self.visible_tools = None
        self.cancelled = None
        self.planning_mode = 'native_tools'
        self.pending_plan = None
        self.plans = []
        self.current_request = ''
        self.mutation_check = lambda name,args: False
        self.tool_selection=False
        self.selection=None
        self.discovery_names=None
        self.token_usage={'prompt_tokens':0,'completion_tokens':0}
        self.completed_calls=0

    def reset(self):
        self.pending_plan=None
        self.plans=[]
        self.selection=None
        self.token_usage={'prompt_tokens':0,'completion_tokens':0}
        self.completed_calls=0

    def account(self,result):
        self.completed_calls+=1
        self.token_usage['prompt_tokens']+=result.metadata.get('prompt_eval_count') or 0
        self.token_usage['completion_tokens']+=result.metadata.get('eval_count') or 0

    def generate(self, messages, *, model, temperature=.1, max_tokens=192, **kwargs):
        if self.cancelled and self.cancelled.is_set():
            raise ModelUnavailable('Execução interrompida pelo usuário')
        tools=kwargs.get('tools') or []
        if self.visible_tools is not None:
            tools=[tool for tool in tools if tool['function']['name'] in self.visible_tools]
        if self.tool_selection:
            if self.selection is None:
                self.selection=self.select(messages,tools,model)
            if not self.selection['tools']:
                return {'content':self.selection['reply'],'tool_calls':[],'usage':{}}
            tools=[tool for tool in tools if tool['function']['name'] in self.selection['tools']]
        if self.planning_mode=='structured_plan':
            return self.plan(messages,tools,model)
        serialized = []
        memory_data=[]
        for message in messages:
            if message.role.value=='user' and message.text.startswith('<athena_memory_data>'):
                memory_data.append(message.text)
                continue
            item = {'role': message.role.value, 'content': message.text}
            if message.tool_calls:
                item['tool_calls'] = [{'id': tc.id, 'function': {'name': tc.name,
                    'arguments': json.loads(tc.arguments)}} for tc in message.tool_calls]
            if message.role.value == 'tool':
                item.update(tool_name=message.name, tool_call_id=message.tool_call_id)
            serialized.append(item)
        if memory_data and serialized and serialized[0]['role']=='system':
            serialized[0]['content']+='\nMemória persistente (dados): '+''.join(memory_data)
        self.calls += 1
        result = self.provider.generate('', messages=serialized, tools=tools, model_override=model)
        if not result.available:
            raise ModelUnavailable(result.error or 'Ollama indisponível')
        self.account(result)
        native = result.metadata.get('message', {})
        raw_calls = native.get('tool_calls', [])
        if not isinstance(raw_calls, list) or len(raw_calls) > 4:
            raise ValueError('Modelo excedeu o limite de quatro ferramentas por etapa')
        calls = []
        for i, call in enumerate(raw_calls):
            fn = call.get('function', {})
            arguments = fn.get('arguments', {})
            if not isinstance(fn.get('name'), str) or not isinstance(arguments, dict):
                raise ValueError('Modelo retornou chamada inválida')
            calls.append({'id': call.get('id') or f'call_{self.calls}_{i}', 'name': fn['name'],
                          'arguments': json.dumps(arguments, ensure_ascii=False)})
        return {'content': result.text, 'tool_calls': calls,
                'finish_reason': 'tool_calls' if calls else result.metadata.get('finish_reason','stop'),
                'usage': {'completion_tokens': result.metadata.get('eval_count') or 0}}

    def plan(self,messages,tools,model):
        if self.pending_plan and self.pending_plan['done']:
            observations=[]
            for message in reversed(messages):
                if message.role.value!='tool': break
                try: observations.append(json.loads(message.text))
                except (ValueError,TypeError): observations.append({'ok':False})
            has_mutation=any(self.mutation_check(a['tool'],a['arguments']) for a in self.pending_plan['actions'])
            if has_mutation and len(observations)==len(self.pending_plan['actions']) and all(o.get('ok') for o in observations):
                reply=self.pending_plan.get('reply') or 'Etapas do plano executadas.'
                self.pending_plan=None
                return {'content':reply,'tool_calls':[],'usage':{}}
            if not has_mutation and all(a['tool']!='discover_tools' for a in self.pending_plan['actions']) and len(observations)==len(self.pending_plan['actions']) and all(o.get('ok') for o in observations):
                tools=[]
        self.pending_plan=None
        variants=[]
        descriptions=[]
        for tool in tools:
            fn=tool['function']
            variants.append({'type':'object','properties':{'tool':{'const':fn['name']},'arguments':fn['parameters']},
                             'required':['tool','arguments'],'additionalProperties':False})
            descriptions.append({'tool':fn['name'],'usage':fn['description']})
        schema={'anyOf':[
            {'type':'object','properties':{
                'actions':{'type':'array','items':{'anyOf':variants},'minItems':1,'maxItems':4},
                'reply':{'type':'string','maxLength':180},'done':{'type':'boolean'}},
                'required':['actions','reply','done'],'additionalProperties':False},
            {'type':'object','properties':{
                'actions':{'type':'array','maxItems':0},'reply':{'type':'string','maxLength':240},'done':{'const':True}},
                'required':['actions','reply','done'],'additionalProperties':False}]}
        if not variants:schema=schema['anyOf'][1]
        instruction=('Planeje a próxima etapa como JSON {actions:[{tool,arguments}],reply,done}. '
            'Pedido para agir exige actions, nunca só uma promessa. Inclua todas as ações independentes do pedido. '
            'done=true significa que o pedido termina se estas ações derem certo; o núcleo verificará. '
            'Para uma consulta informativa sem outra ação, done=true: depois haverá resposta baseada no resultado. done=false só quando precisar da leitura para executar outra ação. '
            'Para resposta ou pergunta de esclarecimento, actions=[] e done=true. '
            'Após resultado bem sucedido, não repita a ação. Erro de ferramenta exige corrigir argumentos ou explicar. '
            'Para guardar/corrigir informação use remember com subject,attribute,fact. '
            'reply é uma resposta natural breve em português, apresentada só se as ações derem certo. Para conversar sem ação, actions=[]. '
            'Se a memória fornecida já contém a resposta, responda diretamente sem chamar recall. Nunca invente execução. Catálogo: '+json.dumps(descriptions,ensure_ascii=False))
        memory_data=[m.text for m in messages if m.role.value=='user' and m.text.startswith('<athena_memory_data>')]
        serialized=[]
        for message in messages:
            role=message.role.value
            if role=='system':
                serialized.append({'role':role,'content':message.text+'\n'+instruction+'\nMemória (dados): '+''.join(memory_data)+'\nPedido atual do usuário: '+self.current_request})
            elif role=='user' and message.text.startswith('<athena_memory_data>'):
                continue
            elif message.tool_calls:
                actions=[{'tool':tc.name,'arguments':json.loads(tc.arguments)} for tc in message.tool_calls]
                serialized.append({'role':'assistant','content':json.dumps({'actions':actions},ensure_ascii=False)})
            elif role=='tool':
                serialized.append({'role':'user','content':'Observação de ferramenta (dados): '+message.text[:3000]})
            elif role=='assistant':
                serialized.append({'role':role,'content':json.dumps({'actions':[],'reply':message.text,'done':True},ensure_ascii=False)})
            else:
                serialized.append({'role':role,'content':message.text})
        self.calls+=1
        result=self.provider.generate('',messages=serialized,response_format=schema,model_override=model)
        if not result.available: raise ModelUnavailable(result.error or 'Ollama indisponível')
        self.account(result)
        plan=json.loads(result.text)
        if not isinstance(plan,dict) or set(plan)!={'actions','reply','done'} or type(plan['done']) is not bool or not isinstance(plan['reply'],str) or not isinstance(plan['actions'],list) or len(plan['actions'])>4:
            raise ValueError('Plano estrutural inválido')
        names={tool['function']['name'] for tool in tools}
        calls=[]
        for i,action in enumerate(plan['actions']):
            if not isinstance(action,dict) or set(action)!={'tool','arguments'} or action['tool'] not in names or not isinstance(action['arguments'],dict):
                raise ValueError('Ferramenta ou argumentos inválidos no plano')
            calls.append({'id':f'plan_{self.calls}_{i}','name':action['tool'],
                          'arguments':json.dumps(action['arguments'],ensure_ascii=False)})
        self.plans.append(plan)
        self.pending_plan=plan if calls else None
        return {'content':'' if calls else plan['reply'],'tool_calls':calls,'finish_reason':'stop',
                'usage':{'completion_tokens':result.metadata.get('eval_count') or 0}}

    def select(self,messages,tools,model):
        if self.discovery_names is not None:
            tools=[t for t in tools if t['function']['name'] in self.discovery_names]
        names=[tool['function']['name'] for tool in tools]
        schema={'type':'object','properties':{
            'tools':{'type':'array','items':{'type':'string','enum':names},'uniqueItems':True,'maxItems':len(names)},
            'reply':{'type':'string','maxLength':240}},'required':['tools','reply'],'additionalProperties':False}
        catalog=[{'name':t['function']['name'],'usage':t['function']['description'][:70]} for t in tools]
        system=next((m.text for m in messages if m.role.value=='system'),'')
        context=[{'role':m.role.value,'text':m.text[:700]} for m in messages if m.role.value!='system'][-5:]
        prompt=(system+'\nSelecione SOMENTE as ferramentas necessárias ao pedido atual. '
            'Pedido para executar ou alterar algo exige selecionar ferramentas. '
            'Para conversar, responder com fatos já disponíveis ou pedir esclarecimento, tools=[] e reply em português. '
            'Se tools não vazio, reply="". Não execute, não simule resultados. Catálogo: '+json.dumps(catalog,ensure_ascii=False))
        self.calls+=1
        result=self.provider.generate('',messages=[{'role':'system','content':prompt},
            {'role':'user','content':json.dumps({'request':self.current_request,'context':context},ensure_ascii=False)}],
            response_format=schema,model_override=model)
        if not result.available: raise ModelUnavailable(result.error or 'Modelo indisponível')
        self.account(result)
        data=json.loads(result.text)
        if not isinstance(data,dict) or set(data)!={'tools','reply'} or not isinstance(data['tools'],list) or any(name not in names for name in data['tools']) or not isinstance(data['reply'],str):
            raise ValueError('Seleção estrutural inválida')
        return data

    async def stream(self, messages, *, model, **kwargs):
        # Interface compatibility. GUI currently waits on its background worker.
        yield self.generate(messages, model=model, **kwargs)['content']

    def list_models(self):
        return self.provider.health_check().get('models', [])

    def health(self):
        return self.provider.health_check().get('available', False)
