"""Memory actually used by the active backend, with legacy storage preserved."""
import customtkinter as ctk


class MemoryPanel(ctk.CTkFrame):
    def __init__(self,master,athena):
        super().__init__(master);self.athena=athena
        self.text=ctk.CTkTextbox(self,wrap='word');self.text.pack(fill='both',expand=True,padx=8,pady=8)
        self.button=ctk.CTkButton(self,text='Atualizar memória',command=self.refresh)
        self.button.pack(fill='x',padx=8,pady=(0,8))

    def refresh(self):
        try:
            runtime=getattr(self.athena,'agent_runtime',None)
            if runtime and self.athena.settings.get('agentBackend')=='openjarvis':
                recent=self.athena.conversation_context.recent(6)
                with self.athena.local_tasks.connect() as db:
                    facts=db.execute('SELECT subject,attribute,fact FROM personal_facts WHERE active=1 ORDER BY created DESC LIMIT 20').fetchall()
                    count=db.execute('SELECT count(*) FROM personal_facts WHERE active=1').fetchone()[0]
                    history=db.execute('SELECT count(*) FROM personal_facts WHERE active=0').fetchone()[0]
                lines=['MEMÓRIA DA ATHENA','', 'Curta — conversa recente:']
                lines += [item['speaker']+': '+item['content'][:220] for item in recent]
                lines += ['', 'Operacional — experiências e tarefas:']
                lines += [run['status']+' — '+run['request'][:160] for run in runtime.store.recent()[:6]]
                lines += ['', f'Longa — {count} fatos ativos; {history} versões anteriores preservadas:']
                lines += [subject+' / '+attribute+': '+fact[:500] for subject,attribute,fact in facts]
                lines += ['', 'O banco e os modelos de memória anteriores continuam preservados.']
            else:
                memory=self.athena.memory
                lines=['MEMÓRIA ANTERIOR',f'Curta: {memory.count_short_term_memory()}',
                    f'Média: {memory.count_mid_term_memory()}',f'Longa: {memory.count_real_long_term_memory()}']
            self._write('\n'.join(lines))
        except Exception as error:self._write('Não consegui atualizar a memória: '+str(error))

    def _write(self,text):
        self.text.configure(state='normal');self.text.delete('1.0','end');self.text.insert('end',text);self.text.configure(state='disabled')
