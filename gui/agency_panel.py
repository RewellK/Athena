"""Live tasks, goals and learned procedures, instead of proposed-plan counters."""
from contextlib import nullcontext
from pathlib import Path
import subprocess
import sys
import customtkinter as ctk


class AgencyPanel(ctk.CTkFrame):
    STATES={'pending':'aguardando','running':'executando','answered':'respondido',
        'needs_attention':'precisa de atenção','interrupted':'interrompido',
        'cancelled':'cancelado','completed':'concluído','failed':'falhou'}

    def __init__(self, master, athena, task_runner=None):
        super().__init__(master)
        self.athena=athena;self.task_runner=task_runner;self.skills={};self.last_result=''
        self.text=ctk.CTkTextbox(self,wrap='word',height=220)
        self.text.pack(fill='both',expand=True,padx=8,pady=8)
        self.goal_entry=ctk.CTkEntry(self,placeholder_text='Objetivo para executar em segundo plano...')
        self.goal_entry.pack(fill='x',padx=8,pady=4)
        ctk.CTkButton(self,text='Colocar objetivo na fila',command=self.queue_goal).pack(fill='x',padx=8,pady=4)
        self.skill_var=ctk.StringVar(value='Nenhum procedimento aprendido')
        self.skill_menu=ctk.CTkOptionMenu(self,values=['Nenhum procedimento aprendido'],variable=self.skill_var)
        self.skill_menu.pack(fill='x',padx=8,pady=4)
        self.run_button=ctk.CTkButton(self,text='Executar procedimento sem LLM',command=self.run_skill)
        self.run_button.pack(fill='x',padx=8,pady=4)
        controls=ctk.CTkFrame(self);controls.pack(fill='x',padx=8,pady=4)
        ctk.CTkButton(controls,text='Pausar presença',command=self.pause).pack(side='left',expand=True,padx=4)
        ctk.CTkButton(controls,text='Retomar',command=self.resume).pack(side='left',expand=True,padx=4)
        ctk.CTkButton(self,text='Abrir pasta de trabalho',command=self.open_workspace).pack(fill='x',padx=8,pady=4)
        ctk.CTkButton(self,text='Atualizar tarefas',command=self.refresh).pack(fill='x',padx=8,pady=(4,8))
        self.after(5000,self.refresh_periodic)

    def runtime(self):
        if not hasattr(self.athena,'agent_runtime'):
            from integrations.openjarvis.adapter import OpenJarvisRuntime
            self.athena.agent_runtime=OpenJarvisRuntime(self.athena)
        return self.athena.agent_runtime

    def refresh_periodic(self):
        if self.winfo_exists():
            self.refresh();self.after(5000,self.refresh_periodic)

    def refresh(self):
        try:
            runtime=self.runtime();state=self.athena.runtime_supervisor.get_status()
            lines=['PRESENÇA '+('PAUSADA' if state.get('paused') else 'EM MODO SEGURO' if state.get('safe_mode') else 'ATIVA'),
                   '', 'Objetivos em segundo plano:']
            for goal in runtime.catalog.goals.list()[:8]:
                lines.append(self.STATES.get(goal['status'],goal['status'])+' — '+goal['request'][:120])
            lines+=['','Tarefas locais:']
            for task in self.athena.local_tasks.list()[:8]:
                lines.append(task['kind']+' — '+self.STATES.get(task['status'],task['status']))
            lines+=['','Rotinas recorrentes:']
            for routine in runtime.catalog.routines.list()[:5]:
                lines.append(self.STATES.get(routine['status'],routine['status'])+' — a cada '+str(int(routine['interval']))+' segundos')
            procedures=[s for s in runtime.catalog.procedures.list() if s['status']=='active']
            self.skills={s['name'][:60]+' · '+s['id'][:6]:s['id'] for s in procedures}
            options=list(self.skills) or ['Nenhum procedimento aprendido']
            selected=self.skill_var.get()
            self.skill_menu.configure(values=options)
            if selected not in options:self.skill_var.set(options[0])
            self.run_button.configure(state='normal' if self.skills else 'disabled')
            if self.last_result:lines+=['','Última operação:',self.last_result]
            self._write('\n'.join(lines))
        except Exception as error:self._write('Não consegui atualizar: '+str(error))

    def invoke(self,name,args):
        def work():
            presence=getattr(self.athena,'foreground_presence',None)
            with presence.interaction() if presence else nullcontext():
                return self.runtime().run_tool(name,args)
        def success(response):
            def show():
                self.last_result=response;self.refresh()
            self.after(0,show)
        def failure(error,_stack):
            text='Não executei a operação: '+str(error)
            self.after(0,lambda:self._write(text))
        if self.task_runner:self.task_runner.submit(work,on_success=success,on_error=failure,description='explicit_local_tool')
        else:self._write(work())

    def queue_goal(self):
        request=self.goal_entry.get().strip()
        if request:
            self.goal_entry.delete(0,'end');self.invoke('queue_goal',{'request':request})

    def run_skill(self):
        skill_id=self.skills.get(self.skill_var.get())
        if skill_id:self.invoke('skills',{'operation':'run','skill_id':skill_id})

    def pause(self):
        self.athena.runtime_supervisor.pause(reason='user_gui')
        presence=getattr(self.athena,'foreground_presence',None)
        if presence:presence.cancel_background('pause')
        self.refresh()

    def resume(self):
        self.athena.runtime_supervisor.resume(reason='user_gui');self.refresh()

    def open_workspace(self):
        if sys.platform=='darwin':subprocess.Popen(['/usr/bin/open',str(Path(self.athena.local_tasks.workspace))])

    def _write(self,text):
        self.text.configure(state='normal');self.text.delete('1.0','end');self.text.insert('end',text);self.text.configure(state='disabled')
