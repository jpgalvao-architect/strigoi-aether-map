# SPDX-License-Identifier: GPL-3.0-only
"""Geometric visit order, enriched only by explicitly reviewed passages."""
from heapq import heappush, heappop
import math
from app.modules.routes.models import Vertex,Stop,Leg,FarmRoute


def distance(a,b):return math.hypot(a.x-b.x,a.y-b.y)


def vertex(point):return Vertex(x=point.x,y=point.y)


def segment_distance(p,a,b):
    dx,dy=b.x-a.x,b.y-a.y
    t=max(0,min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/(dx*dx+dy*dy))) if dx or dy else 0
    return math.hypot(p.x-a.x-t*dx,p.y-a.y-t*dy)


def candidates(dataset,map_id,resources):
    # Planning targets are independent of the atlas's visibility/visited filters.
    return [p for p in dataset.all_points if p.enabled and p.map_id==map_id and p.resource_id in resources]


def reviewed_path(start,end,map_id,library):
    graph={}
    for route in library:
        if route.map_id!=map_id:continue
        known={p.id:p for p in route.stops}
        for leg in route.legs:
            if not leg.reviewed or leg.origin=='suggested':continue
            # No spatial snapping: overlapping floors are not an implicit junction.
            a,b=known[leg.start],known[leg.end]
            key=lambda p:(p.id,p.x,p.y)
            cost=sum(distance(x,y) for x,y in zip(leg.vertices,leg.vertices[1:]))
            graph.setdefault(key(a),[]).append((key(b),cost,leg.vertices))
    begin=(start.id,start.x,start.y);target=(end.id,end.x,end.y)
    queue=[(0,0,begin,[])];best={begin:0};serial=0
    while queue:
        cost,_,node,path=heappop(queue)
        if node==target:return path
        if cost>best[node]:continue
        for neighbour,step,vertices in graph.get(node,[]):
            total=cost+step
            if total<best.get(neighbour,float('inf')):
                best[neighbour]=total;serial+=1
                heappush(queue,(total,serial,neighbour,path+vertices[bool(path):]))
    return None


def rebuild(route,*,library=(),keep=True):
    old={(l.start,l.end):l for l in route.legs} if keep else {}
    legs=[];pairs=list(zip(route.stops,route.stops[1:]))
    if route.mode=='loop':pairs.append((route.stops[-1],route.stops[0]))
    for a,b in pairs:
        previous=old.get((a.id,b.id))
        if previous and previous.vertices[0]==vertex(a) and previous.vertices[-1]==vertex(b):
            legs.append(previous.model_copy(deep=True));continue
        path=reviewed_path(a,b,route.map_id,library)
        legs.append(Leg(start=a.id,end=b.id,vertices=path or [vertex(a),vertex(b)],
            origin='edited' if path else 'suggested',reviewed=bool(path)))
    return route.model_copy(update={'legs':legs})


def generate(dataset,map_id,resources,limit=12,mode='loop',start=None,library=()):
    if mode not in ('loop','open') or not 2<=limit<=60:raise ValueError('Configuração de rota inválida')
    points=candidates(dataset,map_id,resources)
    if len(points)<2:raise ValueError('Escolha pelo menos dois locais neste mapa.')
    grouped={key:[p for p in points if p.resource_id==key] for key in dict.fromkeys(resources)}
    grouped={key:rows for key,rows in grouped.items() if rows}
    if limit<len(grouped):raise ValueError('Escolha pelo menos uma parada por alvo.')
    count=min(limit,len(points));seeds=points[::max(1,len(points)//80)][:80]
    def cluster(seed):
        required=[min(rows,key=lambda p:distance(p,seed)) for rows in grouped.values()]
        keys={p.id for p in required}
        return required+sorted((p for p in points if p.id not in keys),key=lambda p:distance(p,seed))[:count-len(required)]
    if start is not None:
        group=cluster(start)
    else:
        # Bound work on dense cube/pet catalogues; never solve a global all-node tour.
        group=min((cluster(seed) for seed in seeds),
            key=lambda g:(max(p.x for p in g)-min(p.x for p in g))+(max(p.y for p in g)-min(p.y for p in g)))
    ordered=[min(group,key=lambda p:distance(p,start)) if start else min(group,key=lambda p:(p.y,p.x,p.id))]
    left=[p for p in group if p.id!=ordered[0].id]
    while left:
        p=min(left,key=lambda p:(distance(ordered[-1],p),p.id));ordered.append(p);left.remove(p)
    # Bounded 2-opt keeps the chosen entry and avoids needless crossings.
    for _ in range(3):
        changed=False
        for i in range(1,len(ordered)-1):
            for j in range(i+1,len(ordered)):
                if mode=='open' and j==len(ordered)-1:continue
                a,b,c,d=ordered[i-1],ordered[i],ordered[j],ordered[(j+1)%len(ordered)]
                if distance(a,c)+distance(b,d)<distance(a,b)+distance(c,d)-1e-10:
                    ordered[i:j+1]=reversed(ordered[i:j+1]);changed=True
        if not changed:break
    names={r.id:r.name for r in dataset.resources}
    title=' + '.join(names.get(r,r) for r in resources)
    route=FarmRoute.model_construct(id=__import__('uuid').uuid4().hex,name=(title+' · '+('circuito' if mode=='loop' else 'só ida'))[:180],
        map_id=map_id,resources=list(resources),mode=mode,
        stops=[Stop(id=p.id,name=p.name,x=p.x,y=p.y,resource_id=p.resource_id) for p in ordered],legs=[])
    return FarmRoute.model_validate(rebuild(route,library=library).model_dump())


def validate_references(route,dataset):
    if route.map_id not in {m.id for m in dataset.maps}:raise ValueError('O mapa da rota não está disponível.')
    known={p.id:p for p in dataset.all_points}
    for stop in route.stops:
        if stop.custom:continue
        p=known.get(stop.id)
        if not p or not p.enabled or p.map_id!=route.map_id or p.resource_id!=stop.resource_id or distance(p,stop)>1e-8:
            raise ValueError('A base mudou. Revise os locais desta rota antes de iniciar.')
