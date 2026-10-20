"""Single executable: desktop window or explicitly selected resident mode."""
import json
import os
from pathlib import Path
import sys
import traceback


def main():
    from desktop.paths import prepare_home
    os.umask(0o077)
    home=prepare_home();os.chdir(home)
    log=(home/'logs'/'application.log').open('a',buffering=1)
    sys.stdout=sys.stderr=log
    try:
        if not any(flag in sys.argv for flag in ('--self-test','--gui-smoke')):
            from desktop.ollama_service import ensure_local_ollama
            ensure_local_ollama(home)
        if '--resident' in sys.argv:
            from resident import run
            run(once='--once' in sys.argv)
        elif '--self-test' in sys.argv:
            from brain.orchestrator import Athena
            from runtime.process_lease import close_core
            from integrations.openjarvis.adapter import OpenJarvisRuntime
            import customtkinter
            core=Athena()
            try:
                core.agent_runtime=OpenJarvisRuntime(core)
                core.agent_runtime.run_tool('create_note',{'text':'Teste do aplicativo Athena'})
                from voice.speakers import SpeakerProfiles
                speaker_dimension=SpeakerProfiles(core.local_tasks,core.settings).load().dim
                result={'speaker_model_dimensions':speaker_dimension,'ok':True,'frozen':bool(getattr(sys,'frozen',False)),
                        'python':sys.version.split()[0],'data_home':str(home),
                        'gui_dependency':customtkinter.__version__}
                (home/'self-test.json').write_text(json.dumps(result))
            finally:close_core(core)
        elif '--audio-test' in sys.argv:
            from voice.local_input import LocalVoiceInput
            from core.settings import Settings
            result=LocalVoiceInput(Settings()).transcribe(sys.argv[sys.argv.index('--audio-test')+1])
            (home/'audio-test.json').write_text(json.dumps(result,ensure_ascii=False))
        elif '--gui-smoke' in sys.argv:
            os.environ['ATHENA_DISABLE_MENU']='1'
            from gui.main_window import AthenaDesktopApp
            from runtime.process_lease import close_core,foreground_session
            with foreground_session():
                app=AthenaDesktopApp();app.after(10000,app.quit);app.mainloop()
                app.athena.cancel_current_turn(reason='shutdown')
                app.task_runner.shutdown();close_core(app.athena);app.destroy()
                (home/'gui-smoke.json').write_text(json.dumps({'ok':True,'status_callback_delivered':not app.self_status_panel.loading}))
        else:
            from desktop.helpers import prepare_helpers
            prepare_helpers(Path(sys.executable).parents[2],home)
            from desktop.service import install
            install()
            from app import main as desktop_main
            desktop_main()
    except Exception:
        traceback.print_exc()
        if '--resident' not in sys.argv and '--self-test' not in sys.argv and '--gui-smoke' not in sys.argv:
            import subprocess
            subprocess.run(['/usr/bin/osascript','-e','display alert "Athena" message "Não consegui abrir. Consulte application.log na pasta de dados da Athena."'],check=False)
        raise
    finally:
        log.flush()


if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
