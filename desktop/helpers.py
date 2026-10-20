"""Distinct bundle identities let Finder open the window while helpers stay alive."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess


def resident_executable(home):return Path(home)/'bin/AthenaResident.app/Contents/MacOS/Athena'
def menu_executable(home):return Path(home)/'bin/AthenaStatus.app/Contents/MacOS/AthenaStatus'


def prepare_helpers(application,home):
    application=Path(application).absolute();home=Path(home)
    definitions=[('AthenaResident','Athena','local.athena.resident',application/'Contents/MacOS/Athena'),
                 ('AthenaStatus','AthenaStatus','local.athena.status',application/'Contents/Frameworks/AthenaStatus')]
    changed=False
    for bundle_name,executable,identifier,source in definitions:
        bundle=home/'bin'/(bundle_name+'.app');contents=bundle/'Contents';binary=contents/'MacOS'/executable
        matches=binary.is_file() and hashlib.sha256(binary.read_bytes()).digest()==hashlib.sha256(source.read_bytes()).digest()
        if matches:continue
        contents.mkdir(parents=True,exist_ok=True,mode=0o700);binary.parent.mkdir(exist_ok=True,mode=0o700)
        temporary=binary.with_suffix('.new');shutil.copy2(source,temporary);os.replace(temporary,binary)
        values={'CFBundleIdentifier':identifier,'CFBundleExecutable':executable,'CFBundleName':bundle_name,
                'CFBundlePackageType':'APPL','CFBundleVersion':'1','LSUIElement':True,
                'NSMicrophoneUsageDescription':'Athena usa o microfone no modo de escuta que você ativar.'}
        (contents/'Info.plist').write_bytes(plistlib.dumps(values))
        for name in ('Frameworks','Resources'):
            link=contents/name
            if not link.exists() and not link.is_symlink():link.symlink_to(application/'Contents'/name,target_is_directory=True)
        subprocess.run(['codesign','--force','--sign','-',str(bundle)],check=True,capture_output=True)
        changed=True
    manifest=home/'installation.json';manifest.write_text(json.dumps({'application':str(application),'helpers_separate':True}));manifest.chmod(0o600)
    return changed
