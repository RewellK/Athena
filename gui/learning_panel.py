"""Experiences, proposals and explicit application of tested procedure variants."""
import json
import customtkinter as ctk


class LearningPanel(ctk.CTkFrame):
    def __init__(self,master,core,runner):
        super().__init__(master);self.core=core;self.runner=runner;self.proposals={}
        ctk.CTkLabel(self,text='Experiências e melhorias',font=ctk.CTkFont(size=18,weight='bold')).pack(pady=8)
        self.text=ctk.CTkTextbox(self,wrap='word');self.text.pack(fill='both',expand=True,padx=8,pady=6)
        self.choice=ctk.StringVar(value='Nenhuma proposta')
        self.menu=ctk.CTkOptionMenu(self,variable=self.choice,values=['Nenhuma proposta']);self.menu.pack(fill='x',padx=8,pady=4)
        self.propose_button=ctk.CTkButton(self,text='Revisar experiências e propor uma melhoria',command=self.propose);self.propose_button.pack(fill='x',padx=8,pady=4)
        ctk.CTkButton(self,text='Aprovar proposta selecionada',command=self.approve).pack(fill='x',padx=8,pady=4)
        ctk.CTkButton(self,text='Atualizar experiências',command=self.refresh).pack(fill='x',padx=8,pady=4)
        self.status=ctk.CTkLabel(self,text='',wraplength=390);self.status.pack(padx=8,pady=6)
        self.refresh()
    def workshop(self):return self.core.foreground_presence.workshop
    def refresh(self):
        report=self.workshop().collect();lines=['O QUE APRENDI COM AS EXECUÇÕES','']
        for issue in report['issues']:lines.append(issue['category']+': '+str(issue['count'])+' experiências')
        self.proposals={p['body']['problem'][:65]+' · '+p['id'][:6]:p for p in report['proposals']}
        for name,p in self.proposals.items():
            body=p['body'];lines+=['',body['problem'],'Por quê: '+body['why'],'Proposta: '+body['change'],'Estado: '+p['status']]
        if not report['issues']:lines.append('Ainda não há problemas de execução registrados neste diário.')
        self.text.configure(state='normal');self.text.delete('1.0','end');self.text.insert('end','\n'.join(lines));self.text.configure(state='disabled')
        values=list(self.proposals) or ['Nenhuma proposta'];self.menu.configure(values=values)
        if self.choice.get() not in values:self.choice.set(values[0])
    def propose(self):
        self.propose_button.configure(state='disabled');self.status.configure(text='Revendo experiências com o modelo local...')
        def work():
            with self.core.foreground_presence.interaction():return self.workshop().propose()
        def done(result):
            self.after(0,lambda:(self.propose_button.configure(state='normal'),self.status.configure(text='Revisão concluída.'),self.refresh()))
        def failed(error,_trace):
            text=str(error);self.after(0,lambda:(self.propose_button.configure(state='normal'),self.status.configure(text=text)))
        self.runner.submit(work,on_success=done,on_error=failed,description='review_experiences')
    def approve(self):
        proposal=self.proposals.get(self.choice.get())
        if not proposal:return
        try:
            result=self.workshop().approve(proposal['id'])
            self.status.configure(text='Melhoria aplicada e versionada.' if result.get('applied') else 'Proposta exportada para implementação e testes. O código ativo ainda não mudou.')
            self.refresh()
        except Exception as error:self.status.configure(text=str(error))
