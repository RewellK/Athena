"""Keep writable state outside a frozen/signed application bundle."""
import os
import json
from pathlib import Path
import shutil
import sys


def resources():
    return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))


def data_home():
    override=os.environ.get('ATHENA_HOME')
    if override:
        return Path(override).expanduser().absolute()
    if getattr(sys,'frozen',False):
        return Path.home()/'Library'/'Application Support'/'Athena'
    source=Path(__file__).resolve().parents[1]
    pointer=source/'.athena-installation.json'
    if pointer.exists():
        return Path(json.loads(pointer.read_text())['data_home']).expanduser().absolute()
    return source


def prepare_home():
    home=data_home()
    home.mkdir(parents=True,exist_ok=True,mode=0o700)
    for name in ('config/settings.json','personality/identity.json','personality/system_prompt.txt'):
        target=home/name
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            # Exclusive creation preserves user edits and concurrent first launches.
            try:
                with target.open('xb') as output:
                    output.write((resources()/name).read_bytes())
                target.chmod(0o600)
            except FileExistsError:
                pass
    (home/'logs').mkdir(exist_ok=True,mode=0o700)
    return home
