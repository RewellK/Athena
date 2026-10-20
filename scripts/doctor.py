"""Read-only local diagnostics and optional measured LLM smoke test."""
import argparse
import json
import hashlib
import importlib.util
import os
import subprocess
import platform
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.settings import Settings
from llm.provider import OllamaProvider


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='Executa uma inferência curta local')
    args = parser.parse_args()
    settings = Settings(str(ROOT/'config/settings.json'))
    provider = OllamaProvider(settings)
    report = {'architecture':platform.machine(), 'platform':platform.system(),
        'configured_model':settings.get('ollamaModel'), 'ollama':provider.health_check()}
    vendor=ROOT/'third_party/openjarvis'
    manifest=json.loads((vendor/'UPSTREAM.json').read_text())
    report['execution']={'backend':settings.get('agentBackend'),'planning':settings.get('agentPlanningMode'),
        'tool_selection':settings.get('agentToolSelection'), 'openjarvis_commit':manifest['commit'],
        'upstream_hashes_ok':all(hashlib.sha256((vendor/'openjarvis'/name).read_bytes()).hexdigest()==digest for name,digest in manifest['files_sha256'].items())}
    report['optional_dependencies']={name:importlib.util.find_spec(module) is not None for name,module in
        [('gui','customtkinter'),('browser','playwright'),('speech','faster_whisper'),('microphone','sounddevice')]}
    if sys.platform=='darwin':
        service=subprocess.run(['launchctl','print',f'gui/{os.getuid()}/local.athena.resident'],capture_output=True,text=True)
        report['resident']={'loaded':service.returncode==0,'running':'state = running' in service.stdout}
    try:
        loaded=provider._json('/api/ps',2)
        report['loaded_models']=[{'model':m['name'],'memory_gib':round(m['size']/1024**3,2),'gpu_memory_gib':round(m.get('size_vram',0)/1024**3,2)} for m in loaded.get('models',[])]
    except Exception as error:
        report['loaded_models_error']=str(error)
    if args.smoke:
        result = provider.generate('Responda somente: Athena usa LLMs; LLMs não são Athena.')
        report['smoke'] = {'available':result.available,'text':result.text,'error':result.error,'metrics':result.metadata}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
