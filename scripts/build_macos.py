"""Build a macOS application with embedded Python; never include personal state."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    if sys.platform!='darwin':raise SystemExit('Execute a compilação no macOS de destino.')
    from PIL import Image,ImageDraw
    import PyInstaller.__main__
    work=ROOT/'.build';work.mkdir(exist_ok=True)
    icon=Image.new('RGBA',(1024,1024),(8,18,27,255));draw=ImageDraw.Draw(icon)
    for box,width,color in [((100,100,924,924),24,'#49dbe6'),((145,145,879,879),8,'#225561'),((205,205,819,819),12,'#65f5ed')]:
        draw.ellipse(box,outline=color,width=width)
    draw.line([(320,720),(512,300),(704,720)],fill='#d5ffff',width=48)
    draw.line([(395,585),(629,585)],fill='#d5ffff',width=40)
    icon_path=work/'Athena.icns';icon.save(icon_path)
    args=[str(ROOT/'desktop/launcher.py'),'--name','Athena','--windowed','--onedir','--noconfirm',
        '--distpath',str(ROOT/'dist'),'--workpath',str(work/'pyinstaller'),'--specpath',str(work),
        '--paths',str(ROOT),'--paths',str(ROOT/'third_party/openjarvis'),
        '--icon',str(icon_path),'--osx-bundle-identifier','local.athena.desktop',
        '--collect-all','customtkinter','--collect-all','playwright','--collect-all','sounddevice',
        '--collect-all','faster_whisper','--collect-all','ctranslate2','--collect-all','av',
        '--collect-all','sherpa_onnx','--collect-all','sherpa_onnx_core','--collect-all','onnxruntime','--collect-data','certifi','--collect-all','ddgs',
        '--exclude-module','torch','--exclude-module','tensorflow','--exclude-module','spacy',
        '--exclude-module','pytest','--exclude-module','IPython']
    # Read-only code/defaults/licenses are resources; DB, logs, models and user files
    # are never build inputs. Source copies also preserve architecture inspection.
    paths=subprocess.check_output(['git','ls-files','-co','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    for name in sorted(set(paths)):
        if not name:continue
        path=Path(name)
        if path.parts[0] in ('tests','sources'):
            # sources are copied below without editing the read-only originals.
            if path.parts[0]=='tests':continue
        if path.suffix not in ('.py','.json','.txt','.md') and name!='third_party/openjarvis/LICENSE':continue
        if any(p in ('.git','venv','.athena_workspace','.build','dist','logs') for p in path.parts):continue
        args+=['--add-data',str(ROOT/path)+':'+str(path.parent)]
    vendor=ROOT/'third_party/openjarvis/openjarvis'
    for path in vendor.rglob('*.py'):
        module='openjarvis.'+'.'.join(path.relative_to(vendor).with_suffix('').parts)
        if module.endswith('.__init__'):module=module[:-9]
        args+=['--hidden-import',module]
    status_binary=work/'AthenaStatus'
    if not status_binary.exists() or (ROOT/'desktop/StatusMenu.swift').stat().st_mtime>status_binary.stat().st_mtime:
        subprocess.run(['xcrun','swiftc','-O',str(ROOT/'desktop/StatusMenu.swift'),'-o',str(status_binary)],check=True)
    args+=['--add-binary',str(status_binary)+':.']
    from voice.speakers import MODEL
    speaker_model=ROOT/'.athena_workspace/models/speaker'/MODEL
    if not speaker_model.is_file():raise SystemExit('Prepare o modelo de falantes antes de compilar.')
    args+=['--add-data',str(speaker_model)+':models/speaker']
    PyInstaller.__main__.run(args)
    import plistlib
    plist=ROOT/'dist/Athena.app/Contents/Info.plist'
    values=plistlib.loads(plist.read_bytes())
    values.update(CFBundleDisplayName='Athena',CFBundleShortVersionString='0.1.0',
        NSMicrophoneUsageDescription='Athena usa o microfone somente quando você aciona Falar.',
        NSHighResolutionCapable=True)
    plist.write_bytes(plistlib.dumps(values))
    # Editing Info.plist invalidates the build signature: sign the final bundle.
    subprocess.run(['codesign','--force','--deep','--sign','-',str(ROOT/'dist/Athena.app')],check=True)
    print(ROOT/'dist/Athena.app')


if __name__=='__main__':main()
