"""Learn from reported mistakes by tightening a bounded policy, never permissions."""
import json
import time


class SecurityLearning:
    KINDS={'uncertain_voice','wrong_speaker_reported','identity_clarification','unverified_memory'}
    def __init__(self,tasks):
        self.tasks=tasks
        with tasks.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS security_experiences (
                id INTEGER PRIMARY KEY,kind TEXT NOT NULL,created REAL NOT NULL)''')
            db.execute('''CREATE TABLE IF NOT EXISTS security_policy_versions (
                id INTEGER PRIMARY KEY,threshold REAL NOT NULL,reason TEXT NOT NULL,
                evidence_id INTEGER NOT NULL,created REAL NOT NULL,validation TEXT NOT NULL)''')
    def threshold(self,configured=.8):
        with self.tasks.connect() as db:row=db.execute('SELECT max(threshold) FROM security_policy_versions').fetchone()
        return min(1.,max(.8,float(configured),float(row[0] or 0)))
    def record(self,kind,configured=.8):
        if kind not in self.KINDS:raise ValueError('Tipo de experiência de segurança inválido')
        with self.tasks.connect() as db:
            event=db.execute('INSERT INTO security_experiences(kind,created) VALUES (?,?)',(kind,time.time())).lastrowid
            db.execute('DELETE FROM security_experiences WHERE id NOT IN (SELECT id FROM security_experiences ORDER BY id DESC LIMIT 1000)')
        if kind!='wrong_speaker_reported':return {'recorded':True,'policy_changed':False}
        before=self.threshold(configured);after=max(before,min(.96,round(before+.04,3)))
        # A conservative score gate can be tested exactly, without pretending to
        # have demonstrated better acoustic recognition on real people.
        scores=[.2,.5,.79,.8,.83,.9,.95,1.]
        passed=all(not(score>=after) or score>=before for score in scores) and after>=before
        if not passed:raise RuntimeError('A alteração reduziria a exigência de similaridade')
        if after>before:
            with self.tasks.connect() as db:
                db.execute('INSERT INTO security_policy_versions(threshold,reason,evidence_id,created,validation) VALUES (?,?,?,?,?)',
                    (after,'user_reported_wrong_speaker',event,time.time(),json.dumps({'monotonic_gate_test':True,'acoustic_accuracy_tested':False})))
        return {'recorded':True,'policy_changed':after>before,'before':before,'after':after,
                'explanation':'Exigir maior similaridade após relato de pessoa confundida. Se houver dúvida, perguntar.',
                'validation':'Regra mais conservadora testada; precisão acústica ainda precisa de avaliação humana.'}
    def status(self):
        with self.tasks.connect() as db:
            counts=dict(db.execute('SELECT kind,count(*) FROM security_experiences GROUP BY kind').fetchall())
            revisions=db.execute('SELECT threshold,reason,created,validation FROM security_policy_versions ORDER BY id DESC LIMIT 10').fetchall()
        return {'experiences':counts,'voice_threshold':self.threshold(),'revisions':[dict(zip(('threshold','reason','created','validation'),r)) for r in revisions],
                'invariants':['voice_is_not_authorization','no_permission_expansion','no_raw_audio_in_security_log']}
