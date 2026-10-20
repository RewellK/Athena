"""Explicitly reviewed, context-free read interpretation. Does not train weights."""
import argparse
import os
from pathlib import Path
import sys
import json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.settings import Settings
from language.linguistic_learning_workbench import LinguisticLearningWorkbench
from runtime.process_lease import foreground_session


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--utterance',required=True)
    parser.add_argument('--intent',required=True,choices=['self_identity','user_identity','entity_query','capability_query'])
    parser.add_argument('--target',required=True)
    parser.add_argument('--target-type',required=True,choices=['self','user','entity'])
    parser.add_argument('--approve-context-free',action='store_true',help='Confirma que a interpretação é correta e independe do contexto')
    args=parser.parse_args()
    os.chdir(ROOT); os.umask(0o077)
    with foreground_session():
        settings=Settings()
        bench=LinguisticLearningWorkbench(settings.get('linguisticLearningStorePath'))
        example=bench.save_example({'utterance':args.utterance,'expected_intent':args.intent,'expected_target':args.target,
            'expected_frame':{'target_type':args.target_type},'context':{'reusable_without_context':args.approve_context_free}})
        result=bench.validate_example_as_pattern(example['id']) if args.approve_context_free else example
        print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
