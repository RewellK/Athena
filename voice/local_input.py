"""Push-to-talk local transcription; never opens the microphone at startup."""
from pathlib import Path
import threading


class LocalVoiceInput:
    def __init__(self,settings,workspace='.athena_workspace'):
        self.settings=settings
        self.model=None
        self.lock=threading.RLock()
        self.cancelled=threading.Event()
        self.recording=False
        self.directory=Path(workspace)/'models'/'whisper'

    def load(self,allow_download=False):
        if self.model is not None: return self.model
        from faster_whisper import WhisperModel
        self.directory.mkdir(mode=0o700,parents=True,exist_ok=True)
        self.model=WhisperModel(self.settings.get('speechInputModel','tiny'),device='cpu',compute_type='int8',
            cpu_threads=2,num_workers=1,download_root=str(self.directory),local_files_only=not allow_download)
        return self.model

    def transcribe(self,audio):
        with self.lock:
            model=self.load()
            segments,info=model.transcribe(audio,language='pt',beam_size=1,vad_filter=False)
            text=' '.join(segment.text.strip() for segment in segments if segment.start<60).strip()
            if not text: raise ValueError('Não identifiquei fala. Tente novamente.')
            return {'text':text[:8000],'language':info.language,'local':True}

    def record(self,seconds=6):
        if not self.settings.get('localSpeechInputEnabled',False): raise ValueError('Entrada de voz local desativada')
        import sounddevice as sd
        self.cancelled.clear()
        self.recording=True
        seconds=max(1,min(int(seconds),15))
        # Explicit button/CLI invocation is required; no continuous recording.
        audio=sd.rec(seconds*16000,samplerate=16000,channels=1,dtype='float32')
        try:
            sd.wait()
        finally:
            sd.stop()
            self.recording=False
        if self.cancelled.is_set():
            raise ValueError('Gravação interrompida')
        return self.transcribe(audio[:,0])

    def cancel(self):
        self.cancelled.set()
        if self.recording:
            import sounddevice as sd
            sd.stop()
