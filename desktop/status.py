"""Small native status menu; communication is private local files, no server."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from desktop.paths import resources,data_home


class StatusBroker:
    def __init__(self,core):self.core=core;self.process=None;self.started=False
    def start(self):
        if self.started:return
        self.started=True
        if not getattr(sys,'frozen',False) or sys.platform!='darwin' or os.environ.get('ATHENA_DISABLE_MENU')=='1':return
        from desktop.helpers import menu_executable
        binary=menu_executable(data_home())
        application=Path(sys.executable).parents[2]
        manifest=data_home()/'installation.json'
        if manifest.exists():application=Path(json.loads(manifest.read_text())['application'])
        if binary.exists():
            self.process=subprocess.Popen([str(binary),str(data_home()),str(application)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    def tick(self):
        home=data_home();logs=home/'logs';logs.mkdir(exist_ok=True)
        ambient=self.core.foreground_presence.ambient
        state=self.core.runtime_supervisor.get_status()
        description='pausada' if state.get('paused') else ambient.state if ambient.enabled() else 'presença ativa · escuta desligada'
        if self.core.foreground_presence.interacting.is_set():description='em conversa'
        elif not self.core.foreground_presence.idle.is_set():description='executando objetivo'
        if ambient.error and ambient.enabled():description='erro de escuta'
        output={'updated':time.time(),'state':description,'listening_enabled':ambient.enabled()}
        temporary=logs/'presence-status.json.tmp';temporary.write_text(json.dumps(output));temporary.chmod(0o600);os.replace(temporary,logs/'presence-status.json')
        command=logs/'status-command.json'
        if not command.exists():return
        try:
            if command.stat().st_size>1024:command.unlink();return
            request=json.loads(command.read_text());command.unlink()
            if abs(time.time()-float(request.get('created',0)))>30:return
            action=request.get('command')
            if action in ('microphone_on','microphone_off'):
                self.core.settings.set('ambientListeningEnabled',action=='microphone_on');ambient.cancel();ambient.reset_error()
            elif action=='stop_voice':self.core.voice_engine.stop()
            elif action=='pause':self.core.runtime_supervisor.pause(reason='status_menu');self.core.cancel_current_turn(reason='pause')
            elif action=='resume':self.core.runtime_supervisor.resume(reason='status_menu')
        except (ValueError,OSError,TypeError):return
