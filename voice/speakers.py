"""Basic local speaker similarity. Profiles are opt-in, never authentication."""
import hashlib
import json
from pathlib import Path
import threading
import time

MODEL='3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx'
MODEL_SHA256='357a834f702b80161e5b981182c038e18553c1f2ca752ed6cec2052365d4129b'


class SpeakerProfiles:
    def __init__(self,tasks,settings):
        self.tasks=tasks;self.settings=settings
        from runtime.security_learning import SecurityLearning
        self.security=SecurityLearning(tasks)
        self.extractor=None;self.lock=threading.RLock()
        with tasks.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS speaker_profiles (
                name TEXT PRIMARY KEY, embedding TEXT NOT NULL, samples INTEGER NOT NULL,
                consent_at REAL NOT NULL, model_sha256 TEXT NOT NULL)''')
    def model_path(self):
        local=self.tasks.workspace/'models/speaker'/MODEL
        if local.exists():return local
        from desktop.paths import resources
        return resources()/'models/speaker'/MODEL
    def load(self):
        if self.extractor is not None:return self.extractor
        import sherpa_onnx
        path=self.model_path()
        if not path.is_file():raise ValueError('Modelo de falantes não está instalado.')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=MODEL_SHA256:raise ValueError('Hash do modelo de voz não corresponde ao esperado.')
        config=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(path),num_threads=1,provider='cpu')
        if not config.validate():raise ValueError('Configuração inválida do modelo de falantes')
        self.extractor=sherpa_onnx.SpeakerEmbeddingExtractor(config)
        return self.extractor
    def embedding(self,audio):
        import numpy as np
        samples=np.asarray(audio,dtype='float32').reshape(-1)
        if len(samples)<16000*3 or len(samples)>16000*20:raise ValueError('Use entre 3 e 20 segundos de fala por amostra.')
        if not np.isfinite(samples).all() or float(np.sqrt(np.mean(samples*samples)))<.005:raise ValueError('Amostra silenciosa ou inválida')
        with self.lock:
            extractor=self.load();stream=extractor.create_stream()
            stream.accept_waveform(sample_rate=16000,waveform=samples);stream.input_finished()
            if not extractor.is_ready(stream):raise ValueError('Fala insuficiente para comparar voz')
            vector=np.asarray(extractor.compute(stream),dtype='float32')
        norm=float(np.linalg.norm(vector))
        if not norm or not np.isfinite(vector).all():raise ValueError('Vetor de voz inválido')
        return vector/norm
    def list(self):
        with self.tasks.connect() as db:
            return [{'name':r[0],'samples':r[1],'consent_at':r[2]} for r in db.execute('SELECT name,samples,consent_at FROM speaker_profiles ORDER BY name')]
    def enroll(self,name,audios,consent=False):
        import numpy as np
        name=name.strip()
        if not consent:raise ValueError('A própria pessoa precisa concordar com seu cadastro de voz.')
        if not name or len(name)>100 or len(audios)!=3:raise ValueError('Informe nome e três amostras da mesma pessoa.')
        vectors=[self.embedding(audio) for audio in audios]
        if min(float(np.dot(a,b)) for i,a in enumerate(vectors) for b in vectors[i+1:])<.55:
            raise ValueError('As amostras são inconsistentes. Grave novamente em ambiente tranquilo.')
        center=np.mean(vectors,axis=0);center/=np.linalg.norm(center)
        with self.tasks.connect() as db:
            if db.execute('SELECT 1 FROM speaker_profiles WHERE lower(name)=lower(?)',(name,)).fetchone():
                raise ValueError('Nome já cadastrado. Remova o perfil anterior para refazer.')
            db.execute('INSERT INTO speaker_profiles VALUES (?,?,?,?,?)',(name,json.dumps(center.tolist()),3,time.time(),MODEL_SHA256))
        return {'name':name,'samples':3,'raw_audio_saved':False,'authentication':False}
    def forget(self,name):
        with self.tasks.connect() as db:db.execute('DELETE FROM speaker_profiles WHERE name=?',(name,))
    def identify(self,audio):
        if not self.settings.get('speakerRecognitionEnabled',True):return {'name':None,'reason':'disabled'}
        with self.tasks.connect() as db:rows=db.execute('SELECT name,embedding,model_sha256 FROM speaker_profiles').fetchall()
        if not rows:return {'name':None,'reason':'no_profiles'}
        try:vector=self.embedding(audio)
        except ValueError:return {'name':None,'reason':'insufficient_audio'}
        import numpy as np
        matches=sorted([(float(np.dot(vector,np.asarray(json.loads(embedding),dtype='float32'))),name) for name,embedding,digest in rows if digest==MODEL_SHA256],reverse=True)
        if not matches:return {'name':None,'reason':'model_changed'}
        score,name=matches[0];runner=matches[1][0] if len(matches)>1 else -1
        threshold=self.security.threshold(self.settings.get('speakerSimilarityThreshold',.8))
        if score<threshold or score-runner<.12:
            self.security.record('uncertain_voice')
            return {'name':None,'similarity':round(score,3),'reason':'uncertain'}
        return {'name':name,'similarity':round(score,3),'reason':'voice_similarity','verified_identity':False}
