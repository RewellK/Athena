"""Live local acceptance probe. Failure is reported rather than hidden by mocks."""
import argparse
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.settings import Settings
from llm.provider import OllamaProvider
from conversation.intent_resolution_engine import IntentResolutionEngine


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model')
    parser.add_argument('--timeout',type=float,default=16)
    parser.add_argument('--url',default=None)
    args=parser.parse_args()
    settings=Settings(str(ROOT/'config/settings.json'))
    values=dict(settings.values)
    if args.model: values['ollamaModel']=args.model
    if args.url: values['ollamaUrl']=args.url
    values.update(ollamaFallbackModels=[],ollamaRecoverySeconds=0,intentResolutionTimeoutSeconds=args.timeout)
    identity=json.loads((ROOT/'personality/identity.json').read_text())
    engine=IntentResolutionEngine(OllamaProvider(values),identity,settings=values)
    cases=[('Quem é você?','self_identity',identity['name']),
        ('Quem sou eu?','user_identity',identity['creator']),
        ('Quem é Fernanda?','entity_query','Fernanda'),
        ('Como está o clima hoje?','external_information',None)]
    results=[]
    for message,intent,target in cases:
        started=time.monotonic(); result=engine.resolve(message)
        passed=result.get('available') and result.get('intent')==intent and (target is None or result.get('target')==target)
        if intent=='external_information': passed=passed and result.get('requires_tool')
        row={'message':message,'passed':bool(passed),'seconds':round(time.monotonic()-started,2),'result':result}
        results.append(row); print(json.dumps(row,ensure_ascii=False),flush=True)
    print(json.dumps({'passed':sum(r['passed'] for r in results),'total':len(results),'model':values['ollamaModel']}))
    raise SystemExit(0 if all(r['passed'] for r in results) else 1)


if __name__=='__main__': main()
