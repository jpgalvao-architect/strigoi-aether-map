# SPDX-License-Identifier: GPL-3.0-only
import hashlib
import json
import re
from typing import Literal

from pydantic import Field, FiniteFloat, field_serializer, field_validator, model_serializer, model_validator

from app.core.models import Model

MAP_ID = 'lower-reshanta'
OFFICIAL = 'Siege Global — Default'
LEGACY_OFFICIAL = 'Siege Global v1'
OBJECTIVE_CATEGORY = 'siege-objective'
Sector = Literal['MID', 'BOT', 'TOP']
Action = Literal['regroup', 'attack', 'defend', 'retreat']
Layer = Literal['SiegeObjectives', 'SiegeRings', 'TransitRings', 'Pets', 'Gathering', 'CustomMarkers', 'TacticalShapes']
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
    'CustomMarkers': 'Outros pins',
    'TacticalShapes': 'Formas táticas',
}
COLORS = {
    'SiegeObjectives': '#f8d38b',
    'SiegeRings': '#bdb5ff',
    'TransitRings': '#79d6d0',
    'Pets': '#cc9ce5',
    'Gathering': '#92ddab',
    'CustomMarkers': '#87c8f4',
    'TacticalShapes': '#f8d38b',
}
SOURCE_MAX = 420


class Coordinate(Model):
    x: float = Field(ge=0, le=1, strict=True)
    y: float = Field(ge=0, le=1, strict=True)


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
    def check_ring_identity(self):
        if (self.category == 'siege') != (self.sector is not None):
            raise ValueError('Anel e setor incompatíveis')
        if self.default_callsign and (not self.sector or not self.default_callsign.startswith(PREFIX[self.sector])):
            raise ValueError('Callsign incompatível com o setor')
        return self

    @model_validator(mode='after')
    def check_callsign_position(self):
        if self.default_callsign and self.position is not None and self.position.status != 'verified':
            raise ValueError('Callsign oficial exige posição verificada no setor')
        return self


class CalibratedRing(Ring):
    position: RingPosition

    @model_validator(mode='after')
    def check_callsign_position(self):
        # A manual adjustment keeps its original code while the new position is provisional.
        return self


class RingCatalogue(Model):
    schema_version: Literal[1] = 1
    revision: str = Field(default='legacy-1', pattern=r'^[a-z0-9-]{1,64}$')
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
    id: str = Field(pattern=r'^(local-[a-z0-9-]+|objective-p[1-9][0-9]*)$', max_length=100)
    name: str = Field(min_length=1, max_length=60)
    position: Coordinate
    color: str | None = Field(default=None, pattern=r'^#[0-9a-fA-F]{6}$')
    scale: float = Field(default=1., ge=.65, le=1.8)
    category: str = Field(default='Tático', min_length=1, max_length=32)
    origin: Literal['default', 'custom'] = 'custom'
    visible: bool = Field(default=True, strict=True)

    @field_validator('name', 'category')
    @classmethod
    def clean_text(cls, value):
        value = value.strip()
        if not value or not value.isprintable():
            raise ValueError('Texto de pin inválido')
        return value


DrawingKind = Literal['rectangle', 'ellipse', 'arrow']


class TacticalDrawing(Model):
    id: str = Field(pattern=r'^shape-[a-z0-9-]+$', max_length=100)
    kind: DrawingKind
    start: Coordinate
    end: Coordinate
    color: str | None = Field(default=None, pattern=r'^#[0-9a-fA-F]{6}$')
    width: float = Field(default=2., ge=.75, le=10, strict=True)
    opacity: float = Field(default=.9, ge=.1, le=1, strict=True)
    stroke: Literal['dashed', 'solid'] = 'dashed'
    head_size: float = Field(default=15., ge=4, le=36, strict=True)
    label: str = Field(default='', max_length=60)
    visible: bool = Field(default=True, strict=True)

    @field_validator('label')
    @classmethod
    def validate_label(cls, value):
        value = value.strip()
        if value and not value.isprintable():
            raise ValueError('Texto da forma inválido.')
        return value

    @model_validator(mode='after')
    def check_geometry(self):
        dx, dy = abs(self.start.x-self.end.x), abs(self.start.y-self.end.y)
        if (max(dx, dy) if self.kind == 'arrow' else min(dx, dy)) < 1e-6:
            raise ValueError('Arraste para dar tamanho à forma.')
        return self


class PublishedRing(Ring):
    display_code: str | None = Field(default=None, pattern=r'^[A-Z]{1,2}[1-9][0-9]*$', max_length=16)

    @model_validator(mode='after')
    def check_callsign_position(self):
        return self


def ring_catalogue_hash(rings):
    records = [ring.model_dump(mode='json') for ring in rings]
    wire = json.dumps(records, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(wire.encode('utf-8')).hexdigest()


class PublishedRingCatalogue(Model):
    version: Literal[1] = 1
    base_revision: str = Field(pattern=r'^[a-z0-9-]{1,64}$')
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    rings: list[PublishedRing] = Field(max_length=250)

    @model_validator(mode='after')
    def verify_catalogue(self):
        ids = {ring.ring_id for ring in self.rings}
        codes = [ring.display_code for ring in self.rings if ring.display_code]
        if len(ids) != len(self.rings) or len(set(codes)) != len(codes):
            raise ValueError('Identidade de anel duplicada')
        if self.sha256 != ring_catalogue_hash(self.rings):
            raise ValueError('O catálogo de anéis não corresponde à revisão publicada.')
        return self


class Preset(Model):
    model_config = Model.model_config | {'json_schema_extra': {
        'required': ['schema_version', 'map_id', 'name'],
        'allOf': [
            {'if': {'properties': {'schema_version': {'enum': [2, 3]}}}, 'then': {'required': ['markers']}},
            {'if': {'properties': {'schema_version': {'const': 3}}}, 'then': {'required': ['drawings']}},
        ],
    }}

    schema_version: Literal[1, 2, 3] = 3
    map_id: Literal['lower-reshanta'] = MAP_ID
    map_frame: Literal['Abyss_Reshanta_A'] = 'Abyss_Reshanta_A'
    name: str = Field(min_length=1, max_length=70)
    layers: set[Layer] = Field(default_factory=lambda: {'SiegeObjectives', 'SiegeRings'})
    colors: dict[Layer, str] = Field(default_factory=dict)
    use_local_calibration: bool = False
    marker_scale: float = Field(default=1.0, ge=.65, le=1.8)
    aliases: dict[str, str] = Field(default_factory=dict, max_length=250)
    markers: list[CustomMarker] = Field(default_factory=list)
    drawings: list[TacticalDrawing] = Field(default_factory=list)
    calibrated_rings: list[CalibratedRing] = Field(default_factory=list, max_length=250)
    ring_catalogue: PublishedRingCatalogue | None = None

    @model_serializer(mode='wrap')
    def serialize_preset(self, serialize):
        data = serialize(self)
        if self.ring_catalogue is None:
            data.pop('ring_catalogue', None)
        return data

    @field_serializer('layers', when_used='json')
    def serialize_layers(self, layers):
        return sorted(layers)

    @field_validator('schema_version', mode='before')
    @classmethod
    def validate_version(cls, value):
        if type(value) is not int:
            raise ValueError('Versão de marcações inválida')
        return value

    @model_validator(mode='after')
    def check_customizations(self):
        if any(not re.fullmatch(r'#[0-9a-fA-F]{6}', color) for color in self.colors.values()):
            raise ValueError('Cor de marcador inválida')
        if any(not re.fullmatch(r'ring-[a-z0-9-]{1,95}', key) for key in self.aliases):
            raise ValueError('Identificador de anel inválido')
        if any(not alias.strip() or len(alias) > 36 or not alias.isprintable()
               for alias in self.aliases.values()):
            raise ValueError('Apelido inválido')
        if len({m.id for m in self.markers}) != len(self.markers):
            raise ValueError('Marcador local duplicado')
        if len({drawing.id for drawing in self.drawings}) != len(self.drawings):
            raise ValueError('Forma tática duplicada')
        ring_ids = {ring.ring_id for ring in self.calibrated_rings}
        codes = [ring.default_callsign for ring in self.calibrated_rings if ring.default_callsign]
        if len(ring_ids) != len(self.calibrated_rings) or len(set(codes)) != len(codes):
            raise ValueError('Calibração de anel inválida ou duplicada')
        return self


class TacticalCall(Model):
    model_config = Model.model_config | {'frozen': True}

    sector: Sector = 'MID'
    action: Action = 'attack'
    objective: int | None = Field(default=None, ge=1, le=12)
    ring_id: str | None = None


class OverlayOptions(Model):
    map_markers: bool = False
    visible: bool = False
    locked: bool = False
    opacity: float = Field(default=.94, ge=.25, le=1)
    scale: float = Field(default=1, ge=.75, le=1.6)
    position: tuple[int, int] | None = None
    hud_shortcut: str = Field(default='', max_length=40)

    @model_validator(mode='before')
    @classmethod
    def migrate_map_shortcut(cls, settings):
        # Previous previews stored a shortcut for a separate map window.
        if isinstance(settings, dict) and 'map_shortcut' in settings:
            migrated = {key: value for key, value in settings.items() if key != 'map_shortcut'}
            migrated.setdefault('map_markers', True)
            return migrated
        return settings


class SiegeState(Model):
    schema_version: Literal[1, 2, 3] = 3
    selected_preset: str = OFFICIAL
    presets: list[Preset] = Field(default_factory=list, max_length=31)
    local_rings: dict[str, RingPosition] = Field(default_factory=dict, max_length=250)
    local_callsigns: dict[str, str] = Field(default_factory=dict, max_length=250)
    tactical_call: TacticalCall = Field(default_factory=TacticalCall)
    overlay: OverlayOptions = Field(default_factory=OverlayOptions)

    @model_validator(mode='before')
    @classmethod
    def read_legacy_presets(cls, value):
        if isinstance(value, dict) and value.get('schema_version', 1) == 1:
            presets = value.get('presets', [])
            if isinstance(presets, list):
                return {**value, 'presets': [
                    {'schema_version': 1, **preset} if isinstance(preset, dict) else preset for preset in presets
                ]}
        return value

    @model_validator(mode='after')
    def check_presets_and_codes(self):
        names = [preset.name.strip().casefold() for preset in self.presets]
        if len(set(names)) != len(names):
            raise ValueError('Nome de preset duplicado')
        callsigns = list(self.local_callsigns.values())
        if len(set(callsigns)) != len(callsigns) or any(not re.fullmatch(r'[MBT][1-9][0-9]*', code) for code in callsigns):
            raise ValueError('Callsign local inválido ou duplicado')
        return self
