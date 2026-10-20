"""Start an installed local Ollama only when its loopback endpoint is absent."""
from pathlib import Path
import os
import shutil
import socket
import subprocess


def ensure_local_ollama(home):
    try:
        with socket.create_connection(('127.0.0.1',11434),timeout=.5):return {'running':True,'started':False}
    except OSError:pass
    candidates=[shutil.which('ollama'),'/usr/local/bin/ollama','/opt/homebrew/bin/ollama','/Applications/Ollama.app/Contents/Resources/ollama']
    executable=next((path for path in candidates if path and Path(path).is_file() and os.access(path,os.X_OK)),None)
    if not executable:return {'running':False,'started':False,'reason':'Ollama não instalado'}
    environment=os.environ.copy();environment['OLLAMA_HOST']='127.0.0.1:11434'
    log=(home/'logs/ollama-managed.log').open('ab')
    try:process=subprocess.Popen([executable,'serve'],env=environment,stdout=log,stderr=log,start_new_session=True)
    finally:log.close()
    return {'running':False,'started':True,'pid':process.pid}
