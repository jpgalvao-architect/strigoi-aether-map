# SPDX-License-Identifier: GPL-3.0-only
"""Only observed balances are facts; no synthetic caps, recharge or reset rules."""
from typing import Literal
from pydantic import AwareDatetime, Field, model_validator
from app.core.models import Model

RESOURCE_IDS = ('odyle','odyle_charged')
RESOURCES = {
    'odyle': ('Energia de Odyle','Básica','energy'),
    'odyle_charged': ('Odyle recarregada','Reserva recarregada','energy'),
}


class CounterReading(Model):
    value: int = Field(strict=True,ge=0,le=100000)
    observed_at: AwareDatetime
    source: Literal['game-entry-counts-v1'] = 'game-entry-counts-v1'


class RoutineProfile(Model):
    character: str = Field(min_length=1,max_length=80)
    server: int = Field(strict=True,gt=0,le=65535)
    region: Literal['sa','eu','nae','naw','asia','kr','tw']
    job: int = Field(default=0,strict=True,ge=0,le=9)
    counters: dict[Literal['odyle','odyle_charged'],CounterReading] = Field(default_factory=dict,max_length=2)


class RoutineCollection(Model):
    schema_version: Literal[1] = 1
    last_profile: str | None = None
    profiles: dict[str,RoutineProfile] = Field(default_factory=dict,max_length=256)

    @model_validator(mode='after')
    def valid_keys(self):
        if self.last_profile is not None and self.last_profile not in self.profiles:
            raise ValueError('Missing routine profile')
        for key,profile in self.profiles.items():
            if key!=profile_key(profile.region,profile.server,profile.character):
                raise ValueError('Invalid routine profile scope')
        return self


def profile_key(region,server,character):
    import hashlib
    return f'{region}:{server}:{hashlib.sha256(character.encode("utf-8")).hexdigest()[:20]}'
