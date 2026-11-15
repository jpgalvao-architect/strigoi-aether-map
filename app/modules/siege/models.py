# SPDX-License-Identifier: GPL-3.0-only
import re
from typing import Literal

from pydantic import Field, FiniteFloat, model_validator

from app.core.models import Model

MAP_ID = 'lower-reshanta'
OFFICIAL = 'Siege Global v1'
Sector = Literal['MID', 'BOT', 'TOP']
Action = Literal['regroup', 'attack', 'defend', 'retreat']
Layer = Literal['SiegeObjectives', 'SiegeRings', 'TransitRings', 'Pets', 'Gathering', 'CustomMarkers']
SECTORS = {
    'MID': 'Raiz de Reshanta',
    'BOT': 'Arquipélago das Asas de Siel',
    'TOP': 'Ilha da Árvore Sulfúrica',
}
PREFIX = {'MID': 'M', 'BOT': 'B', 'TOP': 'T'}
LAYERS = {
    'SiegeObjectives': 'Objetivos',
    'SiegeRings': 'Anéis de siege',
    'TransitRings': 'Anéis de trânsito',
    'Pets': 'Pets',
    'Gathering': 'Coletas',
    'CustomMarkers': 'Marcadores locais',
}
COLORS = {
    'SiegeObjectives': '#f8d38b',
    'SiegeRings': '#bdb5ff',
    'TransitRings': '#79d6d0',
    'Pets': '#cc9ce5',
    'Gathering': '#92ddab',
    'CustomMarkers': '#87c8f4',
}
SOURCE_MAX = 420


class Coordinate(Model):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class Objective(Model):
    number: int = Field(ge=1, le=12)
    sector: Sector
    map_position: Coordinate
    reference_pixel: tuple[int, int]
    reference_label: str
    status: Literal['reference', 'verified'] = 'reference'

    @property
    def code(self):
        return f'P{self.number}'


class RingPosition(Model):
    map_position: Coordinate
    source: str = Field(min_length=1, max_length=SOURCE_MAX)
    status: Literal['provisional', 'verified']
    world_coordinates: tuple[FiniteFloat, FiniteFloat, FiniteFloat | None] | None = None
    altitude: float | None = Field(default=None, allow_inf_nan=False)


class Ring(Model):
    ring_id: str = Field(pattern=r'^ring-[a-z0-9-]+$', max_length=100)
    map_id: Literal['lower-reshanta'] = MAP_ID
    zone_id: str
    sector: Sector | None = None
    display_name: str
    geographic_description: str = ''
    category: Literal['siege', 'transit']
    source: str
    position: RingPosition | None = None
    default_callsign: str | None = Field(default=None, pattern=r'^[MBT][1-9][0-9]*$')

    @model_validator(mode='after')
    def check_callsign(self):
        if (self.category == 'siege') != (self.sector is not None):
            raise ValueError('Anel e setor incompatíveis')
        if self.default_callsign and (
            self.sector is None or not self.default_callsign.startswith(PREFIX[self.sector])
            or self.position is None or self.position.status != 'verified'
        ):
            raise ValueError('Callsign oficial exige posição verificada no setor')
        return self


class RingCatalogue(Model):
    schema_version: Literal[1] = 1
    map_frame: Literal['Abyss_Reshanta_A/4096-north-up']
    rings: list[Ring] = Field(min_length=1, max_length=250)

    @model_validator(mode='after')
    def check_identity(self):
        ring_ids = [ring.ring_id for ring in self.rings]
        callsigns = [ring.default_callsign for ring in self.rings if ring.default_callsign]
        if len(set(ring_ids)) != len(ring_ids) or len(set(callsigns)) != len(callsigns):
            raise ValueError('Identidade de anel duplicada')
        return self


class Cartography(RingCatalogue):
    objectives: list[Objective]

    @model_validator(mode='after')
    def check_numbering(self):
        for sector, start in zip(SECTORS, (1, 5, 9)):
            numbers = sorted(p.number for p in self.objectives if p.sector == sector)
            if numbers != list(range(start, start + 4)):
                raise ValueError('Numeração dos objetivos inválida')
        return self


class CustomMarker(Model):
    id: str = Field(pattern=r'^local-[a-z0-9-]+$', max_length=100)
    name: str = Field(min_length=1, max_length=60)
    position: Coordinate


class Preset(Model):
    schema_version: Literal[1] = 1
    map_id: Literal['lower-reshanta'] = MAP_ID
    name: str = Field(min_length=1, max_length=70)
    layers: set[Layer] = Field(default_factory=lambda: {'SiegeObjectives', 'SiegeRings'})
    colors: dict[Layer, str] = Field(default_factory=dict)
    use_local_calibration: bool = False
    marker_scale: float = Field(default=1.0, ge=.65, le=1.8)
    aliases: dict[str, str] = Field(default_factory=dict, max_length=250)
    markers: list[CustomMarker] = Field(default_factory=list, max_length=150)

    @model_validator(mode='after')
    def check_customizations(self):
        if any(not re.fullmatch(r'#[0-9a-fA-F]{6}', color) for color in self.colors.values()):
            raise ValueError('Cor de marcador inválida')
        if any(not alias.strip() or len(alias) > 36 or not alias.isprintable()
               for alias in self.aliases.values()):
            raise ValueError('Apelido inválido')
        if len({m.id for m in self.markers}) != len(self.markers):
            raise ValueError('Marcador local duplicado')
        return self


class TacticalCall(Model):
    model_config = Model.model_config | {'frozen': True}

    sector: Sector = 'MID'
    action: Action = 'attack'
    objective: int | None = Field(default=None, ge=1, le=12)
    ring_id: str | None = None


class OverlayOptions(Model):
    visible: bool = False
    locked: bool = False
    opacity: float = Field(default=.94, ge=.25, le=1)
    scale: float = Field(default=1, ge=.75, le=1.6)
    position: tuple[int, int] | None = None
    hud_shortcut: str = Field(default='', max_length=40)
    map_shortcut: str = Field(default='', max_length=40)


class SiegeState(Model):
    schema_version: Literal[1] = 1
    selected_preset: str = OFFICIAL
    presets: list[Preset] = Field(default_factory=list, max_length=30)
    local_rings: dict[str, RingPosition] = Field(default_factory=dict, max_length=250)
    local_callsigns: dict[str, str] = Field(default_factory=dict, max_length=250)
    tactical_call: TacticalCall = Field(default_factory=TacticalCall)
    overlay: OverlayOptions = Field(default_factory=OverlayOptions)

    @model_validator(mode='after')
    def check_presets_and_codes(self):
        names = [preset.name.strip().casefold() for preset in self.presets]
        if OFFICIAL.casefold() in names or len(set(names)) != len(names):
            raise ValueError('Nome de preset reservado ou duplicado')
        callsigns = list(self.local_callsigns.values())
        if len(set(callsigns)) != len(callsigns) or any(not re.fullmatch(r'[MBT][1-9][0-9]*', code) for code in callsigns):
            raise ValueError('Callsign local inválido ou duplicado')
        return self
