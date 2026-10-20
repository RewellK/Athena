"""Visible listening control and a light animated representation of real state."""
import math
import subprocess
import sys
import tkinter as tk
import tkinter.messagebox as messagebox
import customtkinter as ctk


class PresenceIndicator(ctk.CTkFrame):
    def __init__(self,master,core):
        super().__init__(master,fg_color='#091821')
        self.core=core;self.phase=0
        self.canvas=tk.Canvas(self,width=110,height=100,bg='#091821',highlightthickness=0)
        self.canvas.pack(side='left',padx=8)
        self.label=ctk.CTkLabel(self,text='ATHENA',font=ctk.CTkFont(size=16,weight='bold'))
        self.label.pack(side='left',padx=8)
        self.button=ctk.CTkButton(self,text='Ativar escuta ambiente',command=self.toggle)
        self.button.pack(side='right',padx=12)
        self.animate()
    def toggle(self):
        enabled=not self.core.settings.get('ambientListeningEnabled',False)
        self.core.settings.set('ambientListeningEnabled',enabled)
        ambient=self.core.foreground_presence.ambient
        ambient.cancel();ambient.reset_error()
        if not enabled:self.core.voice_engine.stop()
    def animate(self):
        ambient=self.core.foreground_presence.ambient
        enabled=self.core.settings.get('ambientListeningEnabled',False)
        if enabled:
            state=ambient.state
            if ambient.error:state='Erro de escuta: '+ambient.error[:100]
        else:state='Escuta desligada · presença local ativa'
        self.label.configure(text='ATHENA\n'+state)
        self.button.configure(text='Pausar escuta ambiente' if enabled else 'Ativar escuta ambiente')
        self.canvas.delete('all');self.phase=(self.phase+3)%360
        color='#53e2e5' if enabled and not ambient.error else '#597079'
        pulse=(math.sin(self.phase*math.pi/180)+1)*3 if ambient.busy.is_set() or ambient.speaking() else ambient.level*5
        self.canvas.create_oval(18-pulse,13-pulse,92+pulse,87+pulse,outline=color,width=2)
        self.canvas.create_arc(8,3,102,97,start=self.phase,extent=235,outline=color,width=3,style='arc')
        self.canvas.create_arc(26,21,84,79,start=-self.phase,extent=170,outline='#aacdd4',width=1,style='arc')
        self.canvas.create_text(55,50,text='A',fill='#dcffff',font=('Helvetica',22,'bold'))
        self.after(80,self.animate)


class PresencePanel(ctk.CTkScrollableFrame):
    def __init__(self,master,core,dispatch=None):
        super().__init__(master);self.core=core;self.entries={}
        self.dispatch=dispatch or (lambda callback:self.after(0,callback))
        ctk.CTkLabel(self,text='Presença e escuta local',font=ctk.CTkFont(size=18,weight='bold')).pack(pady=8)
        ctk.CTkLabel(self,text='A escuta capta as pessoas próximas. Avise e combine com elas.\nÁudio fica apenas na memória RAM; não há identificação de voz.',wraplength=400).pack(padx=8,pady=6)
        self.status=ctk.CTkLabel(self,text='',wraplength=400);self.status.pack(pady=6)
        for key,label in [('ambientAutoAnswer','Responder perguntas sem chamar Athena'),('ambientLearnObservations','Guardar fatos comuns como observações'),('ambientSpeakAnswers','Falar respostas do modo ambiente')]:
            variable=ctk.BooleanVar(value=core.settings.get(key,True))
            checkbox=ctk.CTkCheckBox(self,text=label,variable=variable,command=lambda k=key,v=variable:core.settings.set(k,v.get()))
            checkbox.pack(anchor='w',padx=12,pady=5)
        ctk.CTkLabel(self,text='Fatos ouvidos — ainda não confirmados').pack(pady=(12,4))
        self.choice=ctk.StringVar(value='Nenhuma observação')
        self.menu=ctk.CTkOptionMenu(self,variable=self.choice,values=['Nenhuma observação']);self.menu.pack(fill='x',padx=12,pady=5)
        ctk.CTkButton(self,text='Confirmar informação selecionada',command=self.confirm).pack(fill='x',padx=12,pady=4)
        ctk.CTkButton(self,text='Esquecer informação selecionada',command=self.dismiss).pack(fill='x',padx=12,pady=4)
        ctk.CTkButton(self,text='Apagar todas as observações de escuta',command=self.clear).pack(fill='x',padx=12,pady=4)
        if sys.platform=='darwin' and getattr(sys,'frozen',False):
            from desktop.service import installed
            self.autostart=ctk.BooleanVar(value=installed())
            ctk.CTkCheckBox(self,text='Continuar em segundo plano e iniciar no login',variable=self.autostart,command=self.toggle_service).pack(anchor='w',padx=12,pady=12)
        ctk.CTkButton(self,text='Abrir pasta de dados',command=self.open_data).pack(fill='x',padx=12,pady=4)
        ctk.CTkLabel(self,text='Cadastro local de vozes',font=ctk.CTkFont(size=16,weight='bold')).pack(pady=(12,4))
        self.speaker_name=ctk.CTkEntry(self,placeholder_text='Nome da pessoa presente');self.speaker_name.pack(fill='x',padx=12,pady=4)
        self.speaker_consent=ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(self,text='Concordo com o cadastro da minha voz neste Mac',variable=self.speaker_consent).pack(anchor='w',padx=12,pady=4)
        self.enroll_button=ctk.CTkButton(self,text='Cadastrar minha voz (3 amostras de 6 s)',command=self.enroll);self.enroll_button.pack(fill='x',padx=12,pady=4)
        ctk.CTkButton(self,text='Esquecer voz do nome informado',command=self.forget_voice).pack(fill='x',padx=12,pady=4)
        ctk.CTkButton(self,text='Athena confundiu quem estava falando',command=self.report_identity_error).pack(fill='x',padx=12,pady=4)
        self.enrollment=ctk.CTkLabel(self,text='',wraplength=370);self.enrollment.pack(padx=12,pady=5)
        self.refresh()
    def enroll(self):
        name=self.speaker_name.get().strip()
        if not name or not self.speaker_consent.get():
            messagebox.showinfo('Cadastro de voz','A própria pessoa deve informar seu nome e marcar que concorda com o cadastro.');return
        self.enroll_button.configure(state='disabled')
        import threading
        self.enrollment_cancel=threading.Event()
        def update(callback):
            try:self.dispatch(callback)
            except (RuntimeError,tk.TclError):pass
        def work():
            import threading
            import sounddevice as sd
            import time
            samples=[]
            try:
                with self.core.foreground_presence.interaction():
                    time.sleep(.5)
                    for index in range(3):
                        if self.enrollment_cancel.is_set():return
                        text=f'Amostra {index+1}/3: fale naturalmente por seis segundos.'
                        update(lambda t=text:self.enrollment.configure(text=t))
                        audio=sd.rec(6*16000,samplerate=16000,channels=1,dtype='float32');sd.wait();sd.stop()
                        samples.append(audio[:,0].copy());time.sleep(.5)
                    if self.enrollment_cancel.is_set():return
                    self.core.foreground_presence.ambient.speakers.enroll(name,samples,consent=True)
                update(lambda:self.enrollment.configure(text='Voz cadastrada localmente. Áudio bruto descartado.'))
            except Exception as error:
                message=str(error)[:200];update(lambda:self.enrollment.configure(text=message))
            finally:
                samples.clear();update(lambda:self.enroll_button.configure(state='normal'))
        self.core.foreground_presence.cancel_background('voice_enrollment')
        import threading
        self.enrollment_thread=threading.Thread(target=work,daemon=True,name='athena-speaker-enrollment');self.enrollment_thread.start()
    def stop_enrollment(self):
        if hasattr(self,'enrollment_cancel'):
            self.enrollment_cancel.set()
            import sounddevice as sd
            sd.stop()
            if hasattr(self,'enrollment_thread'):self.enrollment_thread.join(timeout=3)
    def report_identity_error(self):
        ambient=self.core.foreground_presence.ambient
        result=ambient.speakers.security.record('wrong_speaker_reported',self.core.settings.get('speakerSimilarityThreshold',.8))
        ambient.last_speaker={'name':None}
        self.enrollment.configure(text='Registrei a confusão e aumentei a exigência de similaridade. Vou perguntar quando houver dúvida. Limiar: '+str(result['after']))
    def forget_voice(self):
        name=self.speaker_name.get().strip()
        if name and messagebox.askyesno('Cadastro de voz','Remover o perfil de voz de '+name+'?'):
            self.core.foreground_presence.ambient.speakers.forget(name);self.enrollment.configure(text='Perfil removido.')
    def current(self):return self.entries.get(self.choice.get())
    def confirm(self):
        fact=self.current()
        if fact:
            self.core.agent_runtime.catalog.memory.remember(fact['subject'],fact['fact'],fact['attribute'])
            self.core.foreground_presence.ambient.store.dismiss(fact['id']);self.refresh()
    def dismiss(self):
        fact=self.current()
        if fact:self.core.foreground_presence.ambient.store.dismiss(fact['id']);self.refresh()
    def clear(self):
        if messagebox.askyesno('Escuta ambiente','Apagar os fatos ouvidos ainda não confirmados? A memória confirmada será preservada.'):
            self.core.foreground_presence.ambient.store.clear();self.refresh()
    def toggle_service(self):
        from desktop.service import install,uninstall
        try:
            (install if self.autostart.get() else uninstall)()
        except Exception as error:messagebox.showerror('Presença',str(error));self.autostart.set(not self.autostart.get())
    def open_data(self):
        from desktop.paths import data_home
        subprocess.Popen(['open',str(data_home())])
    def refresh(self):
        ambient=self.core.foreground_presence.ambient
        self.entries={f["subject"]+' / '+f['attribute']+' = '+f['fact'][:65]+' · '+f['id'][:5]:f for f in ambient.store.facts()}
        values=list(self.entries) or ['Nenhuma observação'];self.menu.configure(values=values)
        if self.choice.get() not in values:self.choice.set(values[0])
        self.status.configure(text='Estado: '+ambient.state+'\n'+ambient.error+'\nVozes cadastradas: '+', '.join(p['name'] for p in ambient.speakers.list()))
        self.after(2500,self.refresh)
