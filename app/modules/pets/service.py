# SPDX-License-Identifier: GPL-3.0-only
from datetime import UTC, datetime
from time import monotonic
from PySide6.QtCore import QObject, QTimer, Signal
from app.modules.pets.store import PetStore
from app.modules.pets.farm import PetFarm


class PetService(QObject):
    changed = Signal()
    error = Signal(str)
    status_changed = Signal(str)

    def __init__(self, context, feed=None):
        super().__init__()
        self.context = context
        self.feed = feed
        self.runtime = False
        self.profile_key = None
        self.pending = []
        self.session = ''
        self.sequence = 0
        self.collection_ready = False
        self.identity_ms = None
        self.bind_timer = QTimer(self)
        self.bind_timer.setSingleShot(True)
        self.bind_timer.setInterval(3000)
        self.bind_timer.timeout.connect(self.flush_pending)
        self.status = 'Abra o jogo para sincronizar sua coleção.'
        self.store = PetStore(context.directory)
        self.farm = PetFarm(self.store.catalogue)
        if context.prefs.pets.layer_release != 'pets-v1':
            context.prefs.disabled_categories.add('pets')
            context.prefs.pets.layer_release = 'pets-v1'
        if self.store.warning:
            context.messages.append(self.store.warning)
        if feed:
            feed.message.connect(self.from_feed)
            feed.ended.connect(self.disconnected)
        context.changed.connect(self.ensure_running)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        if value != getattr(self, '_status', None):
            self._status = value
            self.status_changed.emit(value)

    def enable_automatic(self):
        self.runtime = True
        self.ensure_running()

    def ensure_running(self):
        if not self.runtime or self.feed is None:
            return
        wanted = self.context.prefs.pets.auto_collection or self.context.prefs.pets.panel_visible
        if wanted:
            self.feed.acquire('pets')
        else:
            self.feed.release('pets')
            self.disconnected()
            self.status = 'Sincronização automática desativada.'

    def disconnected(self):
        self.profile_key = None
        self.collection_ready = False
        self.identity_ms = None
        self.bind_timer.stop()
        self.pending.clear()
        self.session, self.sequence = '', 0
        self.status = 'Aguardando conexão do jogo.'

    def from_feed(self, message):
        if self.feed is None or 'pets' not in self.feed.consumers:
            return
        try:
            self.accept(message)
        except (OSError, ValueError, TypeError, KeyError):
            self.collection_ready = False
            self.status = 'Aguardando atualização da coleção.'

    def accept(self, message):
        kind = message.get('type')
        if kind == 'status':
            if message.get('code') == 'missing_npcap':
                self.status = 'Instale o Npcap para sincronizar com o jogo.'
            elif message.get('reset_zone') is True:
                self.disconnected()
            return
        if kind == 'feed_quality':
            self.collection_ready = False
            self.pending.clear()
            self.bind_timer.stop()
            self.status = 'Aguardando atualização da coleção.'
            return
        if kind != 'event':
            return
        session, sequence = message['session'], message['sequence']
        if session != self.session:
            self.disconnected(); self.session = session
        if sequence <= self.sequence:
            return
        self.sequence = sequence
        event, payload = message['kind'], message['payload']
        if event == 'SelfIdentifiedEvent':
            name, server = payload.get('Name'), payload.get('ServerId')
            if not isinstance(name,str) or not name or type(server) is not int or server<=0:
                return
            expected_region = self.context.prefs.pets.region
            previous = self.profile_key
            # Character separation is conservative until shared scope is validated in SA.
            import hashlib
            key = f'{expected_region}:{server}:{hashlib.sha256(name.encode()).hexdigest()[:20]}'
            if key != previous:
                self.profile_key = self.store.observed_profile(expected_region,server,name)
                self.collection_ready = False
                self.changed.emit()
            self.identity_ms = message['time_ms']
            if self.pending:
                if not self.bind_timer.isActive():
                    self.bind_timer.start()
            elif not self.collection_ready:
                self.status = 'Entre novamente no personagem para sincronizar a coleção.'
            return
        if event not in ('PetCollectionEvent','PetSoulAcquiredEvent','PetLevelReachedEvent'):
            return
        if not self.context.prefs.pets.auto_collection:
            return
        if event == 'PetCollectionEvent' or self.pending or self.profile_key is None:
            if len(self.pending) >= 32:
                self.pending.clear()
                self.collection_ready = False
                self.status = 'Aguardando atualização da coleção.'
                return
            self.pending.append((monotonic(), message))
            if event == 'PetCollectionEvent':
                self.collection_ready = False
            if not self.bind_timer.isActive():
                self.bind_timer.start()
            self.status = 'Identificando sua coleção no jogo.'
            return
        self.collection_event(event,payload)

    def flush_pending(self):
        pending, self.pending = self.pending, []
        if not self.context.prefs.pets.auto_collection or self.profile_key is None:
            return
        for received, queued in pending:
            if monotonic()-received > 10:
                self.collection_ready = False
                continue
            if queued['kind'] == 'PetCollectionEvent' and (
                    self.identity_ms is None or abs(queued['time_ms']-self.identity_ms)>3000):
                self.collection_ready = False
                self.status = 'Aguardando identificação do personagem.'
                continue
            try:
                self.collection_event(queued['kind'], queued['payload'])
            except (OSError, ValueError, TypeError, KeyError):
                self.collection_ready = False
                self.status = 'Aguardando atualização da coleção.'

    def collection_event(self, event, payload):
        stamp = datetime.now(UTC).isoformat()
        records = {}
        if event == 'PetCollectionEvent':
            self.collection_ready = False
            for key, field, maximum in [('Levels','Level',10),('Souls','Souls',100000)]:
                items = payload.get(key)
                if not isinstance(items,list) or len(items)>2048:
                    raise ValueError('Invalid collection list')
                seen = set()
                for item in items:
                    if not isinstance(item,dict):
                        raise ValueError('Invalid collection row')
                    pet_id, value = item.get('PetId'), item.get(field)
                    if type(pet_id) is not int or not 0<pet_id<1000000 or pet_id in seen:
                        raise ValueError('Invalid pet identity')
                    if type(value) is not int or not 0<=value<=maximum:
                        raise ValueError('Invalid pet progress')
                    seen.add(pet_id)
            for item in payload['Levels']:
                if item['PetId'] in self.store.by_id:
                    # The complete soul list is sparse; absence for a named pet means zero.
                    records[item['PetId']] = {'level':item['Level'], 'souls':0, 'pending':False}
            for item in payload['Souls']:
                if item['PetId'] in self.store.by_id:
                    records.setdefault(item['PetId'],{'level':None,'pending':False})['souls'] = item['Souls']
        else:
            pet_id = payload.get('PetId')
            if pet_id not in self.store.by_id:
                return
            entry = self.store.collection.profiles[self.profile_key].entries.get(str(pet_id))
            old = entry.observed if entry else None
            if event == 'PetSoulAcquiredEvent':
                amount = payload.get('Amount')
                if type(amount) is not int or not 0 < amount <= 100000:
                    raise ValueError('Invalid soul gain')
                # A pickup is an increment, never an absolute collection count.
                if not self.collection_ready or old is None or old.souls is None or old.pending:
                    self.status = 'Alma recebida. Entre novamente no personagem para sincronizar o total.'
                    return
                records[pet_id] = {'souls':old.souls+amount}
                costs = self.store.by_id[pet_id].insight_costs
                if costs and old.level is not None and old.level<len(costs) and old.souls+amount>=costs[old.level]:
                    # A source-build threshold can differ by region. Await the game's
                    # authoritative level/count instead of inventing a rollover.
                    records[pet_id] = {'souls':None,'pending':True}
            else:
                level = payload.get('Level')
                if type(level) is not int or not 0 <= level <= 10:
                    raise ValueError('Invalid insight level')
                if old is not None and old.level is not None and level < old.level:
                    return  # Only a fresh absolute collection may lower an observed level.
                records[pet_id] = {'level':level,'pending':False}
                if old is not None and old.level is not None and level > old.level:
                    records[pet_id]['souls'] = 0
        if records or event == 'PetCollectionEvent':
            self.store.accept_snapshot(self.profile_key,records,synced_at=stamp,complete=event=='PetCollectionEvent')
            if event == 'PetCollectionEvent':
                self.collection_ready = True
            self.status = ('Confira a evolução no jogo. As almas serão sincronizadas na próxima entrada.'
                if any(row.get('pending') for row in records.values()) else 'Coleção atualizada pelo jogo.')
            self.changed.emit()

    def shutdown(self):
        self.runtime = False
        self.bind_timer.stop()
        if self.feed:
            self.feed.release('pets')

    def edit(self, pet_id, **changes):
        try:
            self.store.edit(pet_id, **changes)
        except (OSError, ValueError):
            self.error.emit('Não foi possível salvar sua coleção. Tente novamente.')
            return False
        self.changed.emit()
        return True

    def has_farm(self, pet_id):
        return bool(self.farm.by_pet.get(pet_id))

    def sync_map_preferences(self):
        prefs = self.context.prefs
        ids = set()
        for pet in self.store.catalogue.pets:
            entry = self.store.entry(pet.id)
            allowed = (prefs.pets.focus_id is None or prefs.pets.focus_id == pet.id)
            if prefs.pets.map_filter == 'favorites':
                allowed = allowed and entry.favorite
            elif prefs.pets.map_filter == 'needed':
                allowed = allowed and entry.state in ('missing','growing')
            if not allowed:
                ids.add(f'pet-{pet.id}')
        prefs.disabled_resources.difference_update(f'pet-{pet.id}' for pet in self.store.catalogue.pets)
        prefs.disabled_resources.update(ids)

    def record(self, pet_id, level, souls):
        try:
            self.store.record(pet_id, level, souls)
        except (OSError, ValueError):
            self.error.emit('Não foi possível salvar sua coleção. Tente novamente.')
            return False
        self.changed.emit()
        return True
