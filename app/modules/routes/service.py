# SPDX-License-Identifier: GPL-3.0-only
"""Local route library and a fail-closed, transient visit session."""
from time import monotonic
from uuid import uuid4
from PySide6.QtCore import QObject,Signal,QTimer
from app.infrastructure.storage import atomic_json,recover_model,load_model
from app.modules.routes.models import Vertex,Stop,Leg,FarmRoute,RouteLibrary
from app.modules.routes.planner import generate,rebuild,validate_references,distance


class RouteService(QObject):
    changed=Signal()
    library_changed=Signal()

    def __init__(self,context,feed=None):
        super().__init__();self.context=context;self.path=context.directory/'routes.json'
        self.library,warning=recover_model(self.path,RouteLibrary,RouteLibrary())
        if warning:context.messages.append(warning)
        self.draft=None;self.route=None;self.current=0;self.visited=[];self.skipped=[]
        self.paused=False;self.suspended=False;self.allowed=False;self.game=None;self.identity=None
        self.position=None;self.position_at=0.;self.inside_since=None;self.last_arrival=None
        self.recording=False;self.samples=[];self.recordings={};self.generation=0;self._record_broken=True
        self.status='Escolha o que procurar e crie sua rota.'
        self.timer=QTimer(self);self.timer.setInterval(250);self.timer.timeout.connect(self.check_stale);self.timer.start()
        if feed:feed.message.connect(self.from_feed);feed.ended.connect(self.disconnected)
        context.changed.connect(self.validate_active)

    @property
    def dataset(self):return self.context.atlas_dataset

    @property
    def active(self):return self.route is not None

    @property
    def complete(self):return self.active and self.current>=self.total

    @property
    def total(self):return len(self.route.stops)+(self.route.mode=='loop') if self.route else 0

    @property
    def target(self):return self.route.stops[self.current%len(self.route.stops)] if self.active and not self.complete else None

    def notify(self,text=None):
        if text:self.status=text
        self.changed.emit()

    def plan(self,map_id,resources,limit=12,mode='loop',start=None):
        self.draft=generate(self.dataset,map_id,resources,limit,mode,start,self.library.routes)
        self.notify('Circuito sugerido. Confira as passagens antes de sair.')
        return self.draft

    def save(self,route=None):
        route=route or self.draft
        if route is None:raise ValueError('Crie uma rota antes de salvar.')
        validate_references(route,self.dataset)
        collection=self.library.model_copy(deep=True)
        collection.routes=[r for r in collection.routes if r.id!=route.id]+[route.model_copy(deep=True)]
        collection=RouteLibrary.model_validate(collection.model_dump())
        atomic_json(self.path,collection);self.library=collection;self.library_changed.emit()
        self.notify('Rota salva neste computador.')

    def load(self,key):
        route=next(r for r in self.library.routes if r.id==key)
        validate_references(route,self.dataset);self.draft=route.model_copy(deep=True);self.changed.emit()

    def delete(self,key):
        collection=self.library.model_copy(deep=True);collection.routes=[r for r in collection.routes if r.id!=key]
        atomic_json(self.path,collection);self.library=collection;self.library_changed.emit()

    def import_file(self,path):
        if path.stat().st_size>16*1024*1024:raise ValueError('O arquivo de rotas excede 16 MB.')
        incoming=load_model(path,RouteLibrary)
        collection=self.library.model_copy(deep=True)
        for route in incoming.routes:
            validate_references(route,self.dataset)
            route=route.model_copy(deep=True);route.id=uuid4().hex;collection.routes.append(route)
            for leg in route.legs:leg.reviewed=False
        collection=RouteLibrary.model_validate(collection.model_dump())
        atomic_json(self.path,collection);self.library=collection;self.library_changed.emit()

    def export_file(self,path):atomic_json(path,self.library)

    def start(self,route=None):
        route=route or self.draft
        if route is None:raise ValueError('Crie uma rota antes de iniciar.')
        route=FarmRoute.model_validate(route.model_dump())
        validate_references(route,self.dataset)
        self.route=route.model_copy(deep=True);self.current=0;self.visited=[];self.skipped=[]
        self.paused=False;self.suspended=False;self.position=None;self.inside_since=None;self.last_arrival=None
        self.recording=False;self.samples=[];self.recordings={};self.generation+=1;self._record_broken=True
        self.notify('Aguardando minimapa e leitura do personagem.')

    def stop(self):
        self.route=None;self.position=None;self.recording=False;self.samples=[];self.recordings={};self.generation+=1
        self.notify('Rota encerrada.')

    def pause(self):
        if not self.active:return
        self.paused=not self.paused;self.inside_since=None;self.position=None;self.samples=[]
        self._record_broken=True
        if not self.paused:self.suspended=False
        self.notify('Rota pausada.' if self.paused else 'Aguardando uma leitura atual do personagem.')

    def advance(self,*,skipped=False):
        if not self.target:return
        target=self.target
        (self.skipped if skipped else self.visited).append(target.id)
        if self.recording and self.current>0 and self.samples:
            leg=self.route.legs[self.current-1]
            if not skipped and not self._record_broken and len(self.samples)>=2:
                self.recordings[self.current-1]=[leg.vertices[0]]+self.samples+[leg.vertices[-1]]
        self._record_broken=skipped
        self.samples=[self.position] if self.position is not None and not skipped else []
        self.last_arrival=Vertex(x=target.x,y=target.y);self.current+=1;self.inside_since=None
        self.notify('Volta concluída. As paradas visitadas não confirmam coleta.' if self.complete else 'Próxima parada.')

    def skip(self):self.advance(skipped=True)

    def reverse(self):
        if self.draft:
            draft=self.draft.model_copy(deep=True,update={'stops':list(reversed(self.draft.stops))})
            self.draft=rebuild(draft,library=self.library.routes,keep=False);self.changed.emit()

    def edit_passage(self,leg_index,point):
        if self.draft is None:return
        from app.modules.routes.planner import segment_distance
        leg=self.draft.legs[leg_index]
        if len(leg.vertices)>=2000:raise ValueError('Limite de passagens atingido.')
        index=min(range(len(leg.vertices)-1),key=lambda i:segment_distance(point,leg.vertices[i],leg.vertices[i+1]))
        leg.vertices.insert(index+1,point);leg.origin='edited';leg.reviewed=False
        self.changed.emit()

    def add_custom(self,map_id,point):
        if self.draft and len(self.draft.stops)>=60:raise ValueError('Limite de paradas atingido.')
        stop=Stop(id='custom-'+uuid4().hex,name='Ponto próprio',x=point.x,y=point.y,custom=True)
        if not self.draft or self.draft.map_id!=map_id:
            self._custom_first=(map_id,stop);self.draft=None;self.notify('Marque mais um local para criar sua rota.');return
        draft=self.draft.model_copy(deep=True);draft.stops.append(stop)
        self.draft=rebuild(draft);self.changed.emit()

    def custom_pair(self,map_id,point,mode='loop'):
        first=getattr(self,'_custom_first',None)
        if self.draft or first is None or first[0]!=map_id:return self.add_custom(map_id,point)
        first=first[1]
        second=Stop(id='custom-'+uuid4().hex,name='Ponto próprio',x=point.x,y=point.y,custom=True)
        draft=FarmRoute.model_construct(id=uuid4().hex,name='Meus locais · '+('circuito' if mode=='loop' else 'só ida'),map_id=map_id,resources=[],mode=mode,stops=[first,second],legs=[])
        self.draft=rebuild(draft);self._custom_first=None;self.changed.emit()

    def set_context(self,allowed,game):
        if self.game is not None and game is not None and game!=self.game:
            self.paused=True;self.suspended=True;self.samples=[];self.generation+=1
            self._record_broken=True;self.notify('Área ou personagem mudou. Retome a rota quando estiver no mapa correto.')
        self.game=game or self.game;self.allowed=bool(allowed)
        if not allowed:self.lose_position()

    def lose_position(self):
        changed=self.position is not None or self.inside_since is not None
        self.position=None;self.inside_since=None;self.samples=[];self._record_broken=True
        if changed and self.active and not self.paused and not self.complete:self.notify('Aguardando minimapa. Progresso preservado.')

    def observe(self,point,*,map_id,game,observed_at,radius,now=None):
        now=monotonic() if now is None else now
        if (not self.active or self.paused or self.suspended or self.complete or not self.allowed or
                game!=self.game or map_id!=self.route.map_id or not 0<=now-observed_at<=.7 or point is None):
            self.lose_position();return
        if not isinstance(point,Vertex) or not 0<radius<=.01:self.lose_position();return
        if self.position and now-self.position_at<.4 and distance(self.position,point)>.015:
            self.lose_position();return  # Teleport/jump must not join a recorded segment.
        self.position=point;self.position_at=now
        if self.recording and self.current>0 and (not self.samples or distance(self.samples[-1],point)>.0002):
            if len(self.samples)<1998:self.samples.append(point)
            else:self.recording=False;self.samples=[];self.notify('Limite do percurso atingido. Salve antes de continuar.')
        target=self.target
        separation=distance(self.last_arrival,target) if self.last_arrival else None
        if separation:radius=min(radius,separation/3)
        near=distance(point,target)<=radius
        # A close cluster requires a distinct movement before another arrival.
        left_previous=self.last_arrival is None or distance(point,self.last_arrival)>radius*1.6
        if self.context.prefs.routes.auto_advance and near and (self.inside_since is not None or left_previous):
            if self.inside_since is None:self.inside_since=now
            if now-self.inside_since>=.35:self.advance()
        elif not near:self.inside_since=None
        if self.status.startswith(('Aguardando','Indique')):self.notify('Rota em andamento.')

    def check_stale(self):
        if self.position and monotonic()-self.position_at>.8:self.lose_position()

    def from_feed(self,message):
        if message.get('type')=='status' and message.get('reset_zone') is True:self.disconnected();return
        if message.get('type')!='event':return
        payload=message.get('payload',{})
        if message.get('kind')=='SelfIdentifiedEvent':
            key=(payload.get('ServerId'),payload.get('Name'))
            if type(key[0]) is not int or key[0]<=0 or not isinstance(key[1],str) or not key[1].strip():return
            if self.identity is not None and key!=self.identity:self.disconnected()
            self.identity=key
        elif message.get('kind')=='ZoneChangedEvent':self.disconnected()

    def disconnected(self):
        self.identity=None;self.lose_position();self.samples=[];self.generation+=1
        if self.active:
            self.paused=True;self.suspended=True;self.notify('Área ou personagem mudou. Retome a rota quando estiver no mapa correto.')

    def validate_active(self):
        if self.active:
            try:validate_references(self.route,self.dataset)
            except ValueError:
                self.paused=True;self.suspended=True;self.lose_position();self.notify('A base mudou. Revise a rota antes de retomar.')

    def set_recording(self,enabled):
        self.recording=bool(enabled and self.active and not self.complete);self.samples=[];self._record_broken=True
        self.notify('Registrando somente trechos com posição reconhecida.' if self.recording else 'Gravação de percurso pausada.')

    def use_recorded(self):
        if not self.route or not self.recordings:raise ValueError('Ainda não há trechos completos registrados.')
        draft=self.route.model_copy(deep=True)
        for index,vertices in self.recordings.items():
            draft.legs[index].vertices=vertices;draft.legs[index].origin='recorded';draft.legs[index].reviewed=False
        draft.id=uuid4().hex;self.draft=draft;self.changed.emit()

    def reviewed(self):
        if self.draft:
            for leg in self.draft.legs:
                if leg.origin!='suggested':leg.reviewed=True
            self.changed.emit()

    def drawing(self,map_id):
        if not self.active or self.route.map_id!=map_id:return ()
        key=(self.generation,id(self.route),self.current)
        if key==getattr(self,'_drawing_key',None):return self._drawing_lines
        active=self.current-1 if self.current>0 and not self.complete else -1
        self._drawing_key=key
        self._drawing_lines=tuple((tuple((v.x,v.y) for v in l.vertices),l.reviewed,i==active) for i,l in enumerate(self.route.legs))
        return self._drawing_lines

    def shutdown(self):self.timer.stop();self.stop()
