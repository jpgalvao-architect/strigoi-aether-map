# SPDX-License-Identifier: GPL-3.0-only
"""Collection facts and user progress have independent provenance."""
from typing import Literal

from pydantic import Field, field_validator, model_validator
from app.core.models import Model


class MonsterSource(Model):
    npc_code: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=150)


class PetDefinition(Model):
    id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=150)
    family: Literal['Cogni', 'Fera', 'Natura', 'Varian', 'Special']
    portrait: str = Field(pattern=r'^pets/\d+\.png$')
    source: str
    portrait_source: str
    region: Literal['global-reference', 'sa-confirmed']
    checked_on: str
    monsters: list[MonsterSource] = Field(default_factory=list, max_length=300)
    insight_costs: list[int] | None = Field(default=None, max_length=10)

    @field_validator('insight_costs',mode='before')
    @classmethod
    def valid_costs(cls, value):
        if value is not None and (not isinstance(value,list) or any(
                type(cost) is not int or not 0<cost<=100000 for cost in value)):
            raise ValueError('Invalid insight costs')
        return value


class PetCatalogue(Model):
    schema_version: Literal[1] = 1
    checked_on: str
    source_build: str
    coverage: str
    pets: list[PetDefinition] = Field(max_length=2000)

    @model_validator(mode='after')
    def unique_pets(self):
        if len({p.id for p in self.pets}) != len(self.pets):
            raise ValueError('Repeated pet identity')
        return self


class FarmSite(Model):
    id: str
    npc_code: int = Field(gt=0)
    map_id: Literal['altgard', 'verteron']
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    world_lat: float
    world_lng: float
    source: str
    region: Literal['global-reference', 'sa-confirmed']


class PetSites(Model):
    schema_version: Literal[1] = 1
    checked_on: str
    region: Literal['global-reference', 'sa-confirmed']
    coordinate_system: str
    sites: list[FarmSite] = Field(max_length=50000)

    @model_validator(mode='after')
    def unique_sites(self):
        if len({site.id for site in self.sites}) != len(self.sites):
            raise ValueError('Repeated farm site identity')
        return self


class PetProgress(Model):
    level: int | None = Field(default=None, strict=True, ge=0, le=100)
    souls: int | None = Field(default=None, strict=True, ge=0, le=10_000_000)
    pending: bool = False
    origin: Literal['manual', 'observed'] = 'manual'
    updated_at: str = ''


class PetEntry(Model):
    manual: PetProgress | None = None
    observed: PetProgress | None = None
    use_manual: bool = False
    favorite: bool = False
    goal: int = Field(default=1, ge=1, le=100)

    @property
    def progress(self):
        return self.manual if self.use_manual else self.observed or self.manual

    @property
    def state(self):
        progress = self.progress
        if progress is None or progress.level is None or progress.pending:
            return 'unknown'
        if progress.level >= self.goal:
            return 'complete'
        return 'missing' if progress.level == 0 else 'growing'


class PetProfile(Model):
    name: str = Field(min_length=1, max_length=100)
    region: str = 'local'
    server: int | None = Field(default=None, ge=0)
    character: str = Field(default='', max_length=100)
    entries: dict[str, PetEntry] = Field(default_factory=dict, max_length=2000)
    synced_at: str = ''

    @model_validator(mode='after')
    def canonical_keys(self):
        if any(not key.isdecimal() or int(key) <= 0 or str(int(key)) != key for key in self.entries):
            raise ValueError('Noncanonical pet reference')
        return self


class PetCollection(Model):
    schema_version: Literal[1] = 1
    active_profile: str = 'local'
    profiles: dict[str, PetProfile] = Field(default_factory=lambda: {
        'local': PetProfile(name='Minha coleção')}, max_length=100)

    @model_validator(mode='after')
    def profile_exists(self):
        if self.active_profile not in self.profiles:
            raise ValueError('Active collection profile is missing')
        return self
