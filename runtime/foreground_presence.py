"""Presence while CLI/GUI owns the process lease, with priority for the user.

Local tasks/routines need no inference. Queued goals get a separate restricted
view, provider and conversation so background settings never leak into chat.
"""
from contextlib import contextmanager
from types import SimpleNamespace
import threading

from conversation.conversation_context import ConversationContext
from integrations.openjarvis.adapter import OpenJarvisRuntime
from llm.provider import OllamaProvider


class BackgroundSettings:
    LIVE={'localAutonomyEnabled','autonomousLocalSkillLearning','residentGoalsEnabled','fileRoots'}
    def __init__(self,source):
        self.source=source;self.values={};self.refresh()

    def refresh(self):
        mapping=getattr(self.source,'values',None)
        if not isinstance(mapping,dict): mapping=self.source if isinstance(self.source,dict) else {}
        self.values.update(mapping)
        self.values.update(useLLM=False,voiceEnabled=False,messageReceivedSoundEnabled=False,
            computerToolsEnabled=False,browserToolsEnabled=False,allowExternalRequests=False,
            asyncLlmTeacherEnabled=False,autoExecuteActions=False)

    def get(self,name,default=None):
        if name in self.LIVE: return self.source.get(name,default)
        if name=='queuedGoalModelEnabled':return self.source.get(name,self.source.get('useLLM',True))
        if name=='useLLM': return bool(self.values.get(name,False) and self.get('queuedGoalModelEnabled',True))
        return self.values.get(name,default)


class ForegroundPresence:
    def __init__(self,core,interval=5):
        self.core=core;self.interval=interval
        self.stop_event=threading.Event();self.interacting=threading.Event()
        self.idle=threading.Event();self.idle.set()
        self.interaction_lock=threading.Lock();self.interactions=0
        if not hasattr(core,'agent_runtime'):
            core.agent_runtime=OpenJarvisRuntime(core)
        settings=BackgroundSettings(core.settings)
        self.view=SimpleNamespace(settings=settings,identity=core.identity,creator_name=core.creator_name,
            local_tasks=core.local_tasks,memory=core.memory,skill_backend=core.skill_backend,
            conversation_context=ConversationContext(),runtime_supervisor=core.runtime_supervisor,
            last_response_metadata={},llm_provider=OllamaProvider(settings,getattr(core,'logger',None)))
        self.view.agent_runtime=OpenJarvisRuntime(self.view)
        self.view.chat=self.chat_background
        self.worker=self.goal_worker=self.guard=None
        from voice.ambient import AmbientListener
        self.ambient=AmbientListener(core,self)
        from desktop.status import StatusBroker
        self.status_broker=StatusBroker(core)
        from learning.experience_workshop import ExperienceWorkshop
        self.workshop=ExperienceWorkshop(core)
        self.last_review=0

    def chat_background(self,text):
        with self.view.llm_provider.turn_budget():
            return self.view.agent_runtime.chat(text)

    def cancel_background(self,reason='user'):
        self.view.agent_runtime.cancel(reason)
        self.view.llm_provider.cancel_current()
        if hasattr(self,'ambient'):self.ambient.cancel()

    @contextmanager
    def interaction(self):
        with self.interaction_lock:
            self.interactions+=1;self.interacting.set()
        self.cancel_background('foreground_handoff')
        self.idle.wait(timeout=2)
        try:
            yield
        finally:
            with self.interaction_lock:
                self.interactions-=1
                if not self.interactions:self.interacting.clear()

    def start(self):
        if self.worker and self.worker.is_alive():return
        paused=self.core.runtime_supervisor.get_status().get('paused')
        self.core.runtime_supervisor.start(background=False)
        if paused:self.core.runtime_supervisor.pause(reason='restored_pause')
        self.stop_event.clear()
        self.worker=threading.Thread(target=self.loop,daemon=True,name='athena-foreground-presence')
        self.goal_worker=threading.Thread(target=self.goal_loop,daemon=True,name='athena-queued-goals')
        self.guard=threading.Thread(target=self.watch_priority,daemon=True,name='athena-user-priority')
        self.worker.start();self.goal_worker.start();self.guard.start()
        self.ambient.start()
        self.status_broker.start()

    def watch_priority(self):
        while not self.stop_event.wait(.1):
            if self.interacting.is_set():self.cancel_background('foreground_handoff')

    def tick(self):
        self.tick_local()
        self.tick_goals()

    def tick_local(self):
        if hasattr(self.core,"foreground_presence"):self.status_broker.tick()
        state=self.core.runtime_supervisor.get_status()
        if state.get('paused') or state.get('safe_mode'):return
        self.core.runtime_supervisor.heartbeat()
        if not self.core.settings.get('localAutonomyEnabled',True):return
        if __import__('time').monotonic()-self.last_review>300:
            self.workshop.tick();self.last_review=__import__('time').monotonic()
        self.core.local_tasks.run_once()
        self.core.agent_runtime.catalog.routines.tick()

    def tick_goals(self):
        state=self.core.runtime_supervisor.get_status()
        if state.get('paused') or state.get('safe_mode'):return
        enabled=self.core.settings.get('queuedGoalModelEnabled',self.core.settings.get('useLLM',True))
        if self.interacting.is_set() or self.stop_event.is_set() or self.ambient.busy.is_set() or not enabled:return
        self.view.settings.refresh()
        self.idle.clear()
        try:
            self.view.agent_runtime.catalog.goals.tick(self.view)
        finally:self.idle.set()

    def loop(self):
        while not self.stop_event.is_set():
            try:self.tick_local()
            except Exception as error:
                logger=getattr(self.core,'logger',None)
                if logger:logger.log('FOREGROUND_PRESENCE_ERROR',str(error))
            self.stop_event.wait(self.interval)

    def goal_loop(self):
        while not self.stop_event.is_set():
            try:self.tick_goals()
            except Exception as error:
                logger=getattr(self.core,'logger',None)
                if logger:logger.log('FOREGROUND_GOAL_ERROR',str(error))
            self.stop_event.wait(self.interval)

    def stop(self):
        self.stop_event.set();self.cancel_background('shutdown')
        self.ambient.stop()
        for thread in (self.worker,self.goal_worker,self.guard):
            if thread and thread is not threading.current_thread():thread.join()
        self.view.agent_runtime.close()
