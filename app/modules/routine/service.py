# SPDX-License-Identifier: GPL-3.0-only
"""Shared passive feed with a new owner required after every absolute login list."""
from datetime import UTC,datetime
from time import monotonic
from PySide6.QtCore import QObject,Signal
from app.modules.routine.store import RoutineStore


class RoutineService(QObject):
    changed=Signal()
    status_changed=Signal(str)

    def __init__(self,context,feed):
        super().__init__()
        self.context,self.feed=context,feed
        self.store=RoutineStore(context.directory)
        if self.store.warning:context.messages.append(self.store.warning)
        self.runtime=False
        self.session='';self.sequence=0
        self.profile_key=None;self.actor=None;self.fresh=False
        self.pending=None;self.boundary=None;self.entry_key=None
        self.region=context.prefs.routine.region
        self._status='Entre no personagem para sincronizar sua Rotina.'
        feed.message.connect(self.from_feed);feed.ended.connect(self.disconnected)
        context.changed.connect(self.ensure_running)

    @property
    def status(self):return self._status

    @status.setter
    def status(self,value):
        if value!=self._status:
            self._status=value;self.status_changed.emit(value)

    def disconnected(self):
        changed=self.fresh or self.profile_key is not None
        self.profile_key=None;self.actor=None;self.fresh=False
        self.pending=None;self.boundary=None;self.entry_key=None
        self.session='';self.sequence=0
        self.status='Aguardando conexão do jogo.'
        if changed:self.changed.emit()

    def enable_automatic(self):
        self.runtime=True;self.ensure_running()

    def ensure_running(self):
        if self.region!=self.context.prefs.routine.region:
            self.disconnected();self.region=self.context.prefs.routine.region
        if not self.runtime:return
        if self.context.prefs.routine.auto_capture:self.feed.acquire('routine')
        else:
            self.feed.release('routine');self.disconnected()
            self.status='Sincronização da Rotina desativada.'

    def from_feed(self,message):
        if 'routine' not in self.feed.consumers:return
        try:self.accept(message)
        except (ValueError,TypeError,KeyError,OSError):
            # A failed identity write must never leave updates bound to the old
            # character. Keep saved balances, but require a new complete binding.
            self.fresh=False;self.pending=None;self.entry_key=None;self.boundary=None
            self.profile_key=None;self.actor=None
            self.status='Aguardando uma nova leitura de Odyle.'
            self.changed.emit()

    def accept(self,message):
        kind=message.get('type')
        if kind=='status':
            if message.get('reset_zone') is True or message.get('code') in ('Stopped','Error','missing_npcap'):
                self.disconnected()
            if message.get('code')=='missing_npcap':self.status='Instale o Npcap para sincronizar com o jogo.'
            return
        if kind=='feed_quality':
            if message.get('reason')=='pet_record_rejected':return
            self.fresh=False;self.pending=None
            self.status='Aguardando uma nova leitura de Odyle.'
            self.changed.emit();return
        if kind!='event' or not self.context.prefs.routine.auto_capture:return
        session,sequence,stamp=(message[k] for k in ('session','sequence','time_ms'))
        if not isinstance(session,str) or type(sequence) is not int or sequence<1 or type(stamp) is not int or stamp<0:
            raise ValueError('Invalid routine event')
        if session!=self.session:self.disconnected();self.session=session
        if sequence<=self.sequence:return
        self.sequence=sequence
        event,payload=message['kind'],message['payload']
        if event=='OdyleListStartedEvent':
            self.profile_key=None;self.actor=None;self.fresh=False
            self.entry_key=None;self.pending=None;self.boundary=stamp
            self.status='Identificando o personagem da Rotina.'
            self.changed.emit();return
        if event=='SelfIdentifiedEvent':
            name,server,actor,job=(payload.get(k) for k in ('Name','ServerId','ActorId','Class'))
            if not isinstance(name,str) or not name or name.startswith('$') or type(server) is not int or server<=0:
                return
            if type(actor) is not int or actor<=0:return
            job=job if type(job) is int and 0<=job<=9 else 0
            key=self.store.identify(self.region,server,name,job)
            if self.profile_key is not None and key!=self.profile_key:
                self.entry_key=None;self.pending=None
            if key!=self.profile_key or actor!=self.actor:self.fresh=False
            self.profile_key,self.actor=key,actor
            if self.pending is not None:
                queued,received,values=self.pending;self.pending=None
                if self.boundary is not None and 0<=stamp-self.boundary<=30000 and monotonic()-received<=30:
                    self.apply(values)
            if not self.fresh:self.status='Entre novamente no personagem para ler o saldo inicial.'
            self.changed.emit();return
        if event!='OdyleEnergyEvent':return
        basic,charged,key=(payload.get(k) for k in ('Basic','Charged','EntryKey'))
        if any(type(v) is not int or not 0<=v<=100000 for v in (basic,charged)) or type(key) is not int or not 0<key<=0xffffffff:
            raise ValueError('Invalid energy balances')
        if payload.get('FullSnapshot') is True:
            self.entry_key=key;self.fresh=False
            self.profile_key=None;self.actor=None
            if self.boundary is None:self.boundary=stamp
            self.pending=(stamp,monotonic(),(basic,charged));return
        if key!=self.entry_key:return
        if self.pending is not None:
            _,received,_=self.pending
            self.pending=(stamp,received,(basic,charged));return
        if self.profile_key is not None:self.apply((basic,charged))

    def apply(self,values):
        self.store.observe(self.profile_key,*values,stamp=datetime.now(UTC))
        self.fresh=True;self.status='Rotina atualizada pelo jogo.'
        self.changed.emit()

    def profile_status(self,key):
        if key==self.profile_key and self.fresh:return 'Leitura atual'
        profile=self.store.collection.profiles.get(key)
        return 'Registro salvo' if profile and profile.counters else 'Aguardando leitura'

    def shutdown(self):
        self.runtime=False;self.feed.release('routine');self.disconnected()
