# SPDX-License-Identifier: GPL-3.0-only
"""Routes reference real atlas IDs; custom locations remain user-owned."""
from typing import Literal
from uuid import uuid4
from pydantic import Field, model_validator
from app.core.models import Model


class Vertex(Model):
    x: float = Field(ge=0,le=1,allow_inf_nan=False)
    y: float = Field(ge=0,le=1,allow_inf_nan=False)


class Stop(Vertex):
    id: str = Field(min_length=1,max_length=250)
    name: str = Field(min_length=1,max_length=180)
    resource_id: str = Field(default='',max_length=150)
    custom: bool = False


class Leg(Model):
    start: str
    end: str
    vertices: list[Vertex] = Field(min_length=2,max_length=2000)
    origin: Literal['suggested','edited','recorded'] = 'suggested'
    reviewed: bool = False


class FarmRoute(Model):
    id: str = Field(default_factory=lambda:uuid4().hex,min_length=1,max_length=64)
    name: str = Field(min_length=1,max_length=180)
    map_id: str = Field(min_length=1,max_length=80)
    resources: list[str] = Field(default_factory=list,max_length=32)
    mode: Literal['loop','open'] = 'loop'
    stops: list[Stop] = Field(min_length=2,max_length=100)
    legs: list[Leg] = Field(default_factory=list,max_length=100)

    @model_validator(mode='after')
    def coherent(self):
        if len({p.id for p in self.stops})!=len(self.stops):raise ValueError('Paradas duplicadas')
        expected=[(a.id,b.id) for a,b in zip(self.stops,self.stops[1:])]
        if self.mode=='loop':expected.append((self.stops[-1].id,self.stops[0].id))
        if [(leg.start,leg.end) for leg in self.legs]!=expected:raise ValueError('Trajeto não corresponde às paradas')
        by_id={p.id:p for p in self.stops}
        for leg in self.legs:
            for vertex,stop in [(leg.vertices[0],by_id[leg.start]),(leg.vertices[-1],by_id[leg.end])]:
                if abs(vertex.x-stop.x)>1e-8 or abs(vertex.y-stop.y)>1e-8:raise ValueError('Extremidade do trajeto alterada')
        return self


class RouteLibrary(Model):
    schema_version: Literal[1] = 1
    routes: list[FarmRoute] = Field(default_factory=list,max_length=100)

    @model_validator(mode='after')
    def unique_ids(self):
        if len({r.id for r in self.routes})!=len(self.routes):raise ValueError('Rotas duplicadas')
        return self
