"""Prepare Whisper once, transcribe a file, or record one local voice turn."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.settings import Settings
from voice.local_input import LocalVoiceInput
from runtime.process_lease import foreground_session, close_core


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--file')
    parser.add_argument('--seconds',type=int,default=6)
    args=parser.parse_args()
    os.chdir(ROOT);os.umask(0o077)
    voice=LocalVoiceInput(Settings())
    if args.prepare:
        voice.load(allow_download=True);print('Modelo de voz local preparado.');return
    if args.file:
        print(json.dumps(voice.transcribe(args.file),ensure_ascii=False));return
    from brain.orchestrator import Athena
    with foreground_session():
        athena=Athena()
        try:
            text=voice.record(args.seconds)['text'];print('Você:',text)
            print('Athena:',athena.chat(text))
        finally: close_core(athena)


if __name__=='__main__': main()
