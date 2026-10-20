"""Local training data preparation with explicit quality labels and holdout split.

No weight training or model replacement is claimed by this module.
"""
import hashlib
import json
from pathlib import Path
import platform
import time


class LearningLab:
    def __init__(self,tasks):
        self.tasks=tasks
        with tasks.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS run_reviews (run_id TEXT PRIMARY KEY, accepted INTEGER NOT NULL, note TEXT NOT NULL, created REAL NOT NULL)')

    def review(self,run_id,accepted,note):
        with self.tasks.connect() as db:
            run=db.execute('SELECT status FROM agent_runs WHERE id=?',(run_id,)).fetchone()
            if not run: raise ValueError('Execução não encontrada')
            if accepted and run[0] not in {'finished','executed'}:
                raise ValueError('Execução incompleta não pode ser exemplo positivo')
            db.execute('INSERT OR REPLACE INTO run_reviews VALUES (?,?,?,?)',(run_id,int(accepted),note[:2000],time.time()))
        return {'run_id':run_id,'accepted':accepted}

    def status(self):
        with self.tasks.connect() as db:
            runs=db.execute('SELECT count(*) FROM agent_runs').fetchone()[0]
            reviewed=db.execute('SELECT count(*) FROM run_reviews WHERE accepted=1').fetchone()[0]
        return {'runs':runs,'accepted_examples':reviewed,'architecture':platform.machine(),
                'weight_training':'not_installed','automatic_model_replacement':False,
                'next_step':'Quality-reviewed examples and a compatible training backend are required before LoRA/fine-tuning.'}

    def export(self):
        with self.tasks.connect() as db:
            rows=db.execute('''SELECT r.id,r.request,r.response FROM agent_runs r JOIN run_reviews v ON v.run_id=r.id
                WHERE v.accepted=1 AND r.status IN ('finished','executed') ORDER BY r.created''').fetchall()
            examples=[]
            for run_id,request,response in rows:
                steps=db.execute('SELECT tool,arguments,result FROM agent_steps WHERE run_id=? AND status=? ORDER BY id',(run_id,'succeeded')).fetchall()
                if not steps: continue
                messages=[{'role':'user','content':request}]
                for i,(tool,arguments,result) in enumerate(steps):
                    tc_id=f'call_{i}'
                    messages.append({'role':'assistant','content':'','tool_calls':[{'id':tc_id,'type':'function','function':{'name':tool,'arguments':arguments}}]})
                    messages.append({'role':'tool','tool_call_id':tc_id,'name':tool,'content':result})
                messages.append({'role':'assistant','content':response.split('\n\nExecução verificada:')[0]})
                # Similar user requests stay in one split to reduce leakage.
                group=' '.join(request.casefold().split())
                split='validation' if int(hashlib.sha256(group.encode()).hexdigest()[:8],16)%5==0 else 'train'
                examples.append((split,{'messages':messages,'metadata':{'run_id':run_id,'quality':'explicit_review'}}))
        root=Path(self.tasks.workspace)/'training'
        if root.is_symlink(): raise ValueError('Diretório de treino não pode ser link')
        root.mkdir(mode=0o700,exist_ok=True)
        paths={}
        for split in ('train','validation'):
            path=root/(split+'.jsonl')
            if path.is_symlink(): raise ValueError('Arquivo de treino não pode ser link')
            path.write_text(''.join(json.dumps(example,ensure_ascii=False)+'\n' for which,example in examples if which==split),encoding='utf-8')
            path.chmod(0o600); paths[split]=str(path)
        return {'examples':len(examples),'paths':paths,'trained':False,'data_stays_local':True}
