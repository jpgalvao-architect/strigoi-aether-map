# SPDX-License-Identifier: GPL-3.0-only
"""Owns validated local settings and emits tactical state without UI dependencies."""
import re
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QObject, Signal

from pydantic import Field

from app.core.models import Category, Gatherable, MapDefinition, Model, PointOfInterest, Region, Subcategory
from app.infrastructure.storage import PACKAGE, atomic_json, load_model, recover_model
from app.modules.siege.map_setup import LOCAL_MAP, MAP_SIZE, MAP_SOURCE, PREPARED_MAP, validate_map, write_map
from app.modules.siege.models import (
    COLORS, MAP_ID, OFFICIAL, PREFIX, SECTORS, Cartography, Coordinate, CustomMarker,
    Preset, RingCatalogue, RingPosition, SiegeState, TacticalCall,
)
from app.modules.siege.transit_codes import TRANSIT_CODES

RING_SOURCE = 'https://metabot.gg/en/aion-2/map/chaotic-lower-reshanta/flight-rings'
ACTIONS = {'regroup': 'REAGRUPAR', 'attack': 'ATACAR', 'defend': 'DEFENDER', 'retreat': 'RECUAR'}


class SiegeService(QObject):
    changed = Signal()
    map_changed = Signal()
    call_changed = Signal(object)  # Immutable TacticalCall values for local consumers.

    def __init__(self, directory):
        super().__init__()
        self.path = directory / 'siege-command.json'
        self.map_path = directory / LOCAL_MAP
        self.prepared_map_path = directory / PREPARED_MAP
        self.data = load_model(PACKAGE / 'data/siege-cartography.json', Cartography)
        self.ring_path = directory / 'siege-ring-catalogue.json'
        original = RingCatalogue(map_frame=self.data.map_frame, rings=self.data.rings)
        catalogue, catalogue_warning = recover_model(self.ring_path, RingCatalogue, original)
        self.rings = {ring.ring_id: ring for ring in catalogue.rings}
        self.objectives = {objective.number: objective for objective in self.data.objectives}
        self.state, self.warning = recover_model(self.path, SiegeState, SiegeState())
        self.warning = self.warning or catalogue_warning
        self._clear_unusable_call(self.state)
        self.definition = None
        self._base = None
        self._atlas = None
        self.refresh_map()

    def refresh_map(self):
        for path in (self.map_path, self.prepared_map_path):
            if path.exists():
                try:
                    validate_map(path)
                except (OSError, ValueError):
                    continue
                self._set_map(path)
                self.map_changed.emit()
                self.changed.emit()
                return True
        if any(path.exists() for path in (self.map_path, self.prepared_map_path)):
            self.warning = self.warning or 'A imagem local de Reshanta não corresponde à base calibrada.'
        return False

    def _set_map(self, path=None):
        self.definition = MapDefinition(
            id=MAP_ID, name='Chaotic Lower Reshanta', region='abyss', image=str((path or self.map_path).resolve()),
            width=MAP_SIZE, height=MAP_SIZE, source=MAP_SOURCE, supports_overlay=False,
        )
        self._base = self._atlas = None

    def import_map(self, path):
        write_map(self.map_path, validate_map(path))
        self._set_map()
        self.map_changed.emit()
        self.changed.emit()

    def import_catalogue(self, path):
        incoming = load_model(path, RingCatalogue)
        if any(ring.ring_id.startswith('ring-pending-') for ring in incoming.rings):
            raise ValueError('O catálogo local precisa usar identificadores de origem.')
        active = {key: ring for key, ring in self.rings.items() if not key.startswith('ring-pending-')}
        for ring in incoming.rings:
            previous = active.get(ring.ring_id)
            if previous is not None and (previous.default_callsign != ring.default_callsign
                                         or previous.sector != ring.sector):
                raise ValueError('O catálogo não pode trocar o callsign ou setor já fixado de um anel.')
            active[ring.ring_id] = ring
        official = {ring.default_callsign: ring.ring_id for ring in active.values() if ring.default_callsign}
        if any(code in official and official[code] != ring_id for ring_id, code in self.state.local_callsigns.items()):
            raise ValueError('O catálogo conflita com um callsign local já fixado.')
        complete = RingCatalogue(map_frame=incoming.map_frame, rings=list(active.values()))
        atomic_json(self.ring_path, complete)
        self.rings = active
        previous = self.call
        self._clear_unusable_call(self.state)
        if self.call != previous:
            self.call_changed.emit(self.call)
        self.changed.emit()

    def atlas_data(self, base):
        if self.definition is None or any(m.id == MAP_ID for m in base.maps):
            return base
        if base is self._base:
            return self._atlas
        regions = list(base.regions)
        if not any(region.id == 'abyss' for region in regions):
            regions.append(Region(id='abyss', name='Abyss'))
        extra = {'maps': [*base.maps, self.definition], 'regions': regions}
        key = 'reshanta-odyle'
        if not any(r.id == key for r in base.resources):
            data = load_model(PACKAGE / 'data/siege-gathering.json', ReshantaGathering)
            category = next((c.id for c in base.categories if c.id == 'odyle'), None)
            categories = list(base.categories)
            if category is None:
                category = 'reshanta-gathering'
                categories.append(Category(id=category, name='Coletas de Reshanta', icon='diamond', color=COLORS['Gathering']))
            subgroup = 'reshanta-odyle-nodes'
            extra.update(
                categories=categories,
                subcategories=[*base.subcategories, Subcategory(id=subgroup, category=category, name='Odyle')],
                resources=[*base.resources, Gatherable(
                    id=key, name='Lesser Odyle', category=category, subcategory=subgroup,
                    source=data.source, verification='Posições de referência; presença atual não confirmada.',
                )],
                points=[*base.points, *(PointOfInterest(
                    id=f'{key}-{index}', name='Lesser Odyle', map_id=MAP_ID, resource_id=key,
                    x=point.x, y=point.y, source=data.source, certainty='possible', visible_in_overlay=False,
                ) for index, point in enumerate(data.points, 1))],
            )
        self._atlas = base.model_copy(update=extra)
        self._base = base
        return self._atlas

    @property
    def preset(self):
        return next((preset for preset in self.state.presets if preset.name == self.state.selected_preset),
                    Preset(name=OFFICIAL, layers={'SiegeObjectives', 'SiegeRings', 'TransitRings'}))

    @property
    def call(self):
        return self.state.tactical_call

    def _commit(self, **changes):
        candidate = SiegeState.model_validate({**self.state.model_dump(), **changes})
        self._clear_unusable_call(candidate)
        atomic_json(self.path, candidate)
        previous = self.call
        self.state = candidate
        if self.call != previous:
            self.call_changed.emit(self.call)
        self.changed.emit()

    def update_overlay(self, **changes):
        if any(getattr(self.state.overlay, key) != value for key, value in changes.items()):
            self._commit(overlay={**self.state.overlay.model_dump(), **changes})

    def select_preset(self, name):
        if name != OFFICIAL and not any(preset.name == name for preset in self.state.presets):
            raise ValueError('Preset não encontrado.')
        if name != self.state.selected_preset:
            self._commit(selected_preset=name)

    def save_preset(self, preset):
        if preset.name.strip().casefold() == OFFICIAL.casefold():
            raise ValueError('Escolha outro nome para preservar Siege Global v1.')
        if not preset.name.strip() or not preset.name.isprintable() or not preset.aliases.keys() <= self.rings.keys():
            raise ValueError('Nome do preset ou referência a anel inválida.')
        presets = [p for p in self.state.presets if p.name != preset.name] + [preset]
        self._commit(presets=presets, selected_preset=preset.name)

    def edit_preset(self, **changes):
        if self.preset.name == OFFICIAL:
            raise ValueError('Crie uma cópia do preset para editar.')
        self.save_preset(Preset.model_validate({**self.preset.model_dump(), **changes}))

    def import_preset(self, path):
        preset = load_model(path, Preset)
        if any(p.name.strip().casefold() == preset.name.strip().casefold() for p in self.state.presets):
            raise ValueError('Já existe um preset com este nome.')
        self.save_preset(preset)

    def export_preset(self, path):
        atomic_json(path, self.preset)

    def add_marker(self, name, position):
        self.edit_preset(markers=[*self.preset.markers, CustomMarker(
            id=f'local-{uuid4().hex}', name=name, position=position,
        )])

    def _clear_unusable_call(self, state):
        call = state.tactical_call
        changes = {}
        if call.ring_id:
            ring = self.rings.get(call.ring_id)
            if not ring or ring.sector != call.sector or not self.callsign(ring, state=state):
                changes['ring_id'] = None
        if call.objective and self.objectives[call.objective].sector != call.sector:
            changes['objective'] = None
        if changes:
            state.tactical_call = call.model_copy(update=changes)

    def position(self, ring, *, state=None):
        state = self.state if state is None else state
        custom = next((preset for preset in state.presets if preset.name == state.selected_preset), None)
        if custom and custom.use_local_calibration:
            return state.local_rings.get(ring.ring_id) or ring.position
        return ring.position

    def callsign(self, ring, *, state=None):
        state = self.state if state is None else state
        position = self.position(ring, state=state)
        if position is None or position.status != 'verified':
            return None
        if ring.default_callsign:
            return ring.default_callsign
        code = state.local_callsigns.get(ring.ring_id, '')
        if ring.sector and re.fullmatch(
            PREFIX[ring.sector] + r'[1-9][0-9]*', code
        ):
            return code
        return None

    def ring_code(self, ring):
        if ring.category == 'transit':
            return TRANSIT_CODES.get(ring.ring_id)
        return self.callsign(ring) or ring.default_callsign

    def ring_label(self, ring):
        label = self.ring_code(ring) or ring.display_name
        alias = self.preset.aliases.get(ring.ring_id)
        return f'{label} · {alias}' if alias else label

    def calibrate_ring(self, ring_id, position):
        if ring_id not in self.rings:
            raise ValueError('Anel fora do catálogo atual.')
        self._commit(local_rings={**self.state.local_rings, ring_id: position})

    def reset_ring(self, ring_id):
        if ring_id in self.state.local_rings:
            local = dict(self.state.local_rings)
            del local[ring_id]
            self._commit(local_rings=local)

    def freeze_callsigns(self, sector):
        prefix = PREFIX[sector]
        codes = dict(self.state.local_callsigns)
        used = [r.default_callsign for r in self.rings.values() if r.default_callsign]
        used.extend(codes.values())
        latest = max((int(c[1:]) for c in used if re.fullmatch(prefix + r'[1-9][0-9]*', c)), default=0)
        eligible = [r for r in self.rings.values() if r.sector == sector and not r.default_callsign
                    and r.ring_id not in codes and (position := self.state.local_rings.get(r.ring_id) or r.position)
                    and position.status == 'verified']
        # 8 px bands on the canonical frame. Within a band, west comes first.
        def order(ring):
            position = self.state.local_rings.get(ring.ring_id) or ring.position
            point = position.map_position
            altitude = position.altitude if position.altitude is not None else 0
            return (round(point.y * MAP_SIZE / 8), point.x, point.y, altitude, ring.ring_id)

        for index, ring in enumerate(sorted(eligible, key=order), latest + 1):
            codes[ring.ring_id] = f'{prefix}{index}'
        if codes != self.state.local_callsigns:
            self._commit(local_callsigns=codes)
        return len(eligible)

    def select_sector(self, sector):
        if sector != self.call.sector:
            self.set_call(sector=sector, ring_id=None, objective=None)

    def set_call(self, **changes):
        call = TacticalCall.model_validate({**self.call.model_dump(), **changes})
        if call.objective is not None and self.objectives[call.objective].sector != call.sector:
            raise ValueError('O objetivo pertence a outro setor.')
        if call.ring_id is not None:
            ring = self.rings.get(call.ring_id)
            if ring is None or ring.sector != call.sector or not self.callsign(ring):
                raise ValueError('Selecione um anel verificado com callsign no setor.')
        if call != self.call:
            self._commit(tactical_call=call)

    def call_text(self, translate=lambda text: text):
        call = self.call
        ring = self.rings.get(call.ring_id)
        code = self.callsign(ring) if ring else None
        objective = f'P{call.objective}' if call.objective is not None else None
        action = translate(ACTIONS[call.action])
        if call.action in ('regroup', 'retreat'):
            target = code or objective
            return f'{action} {target}' if target else ''
        if objective is None:
            return ''
        lead = f'{translate(ACTIONS["regroup"])} {code} → ' if code else ''
        return f'{lead}{action} {objective}'



class ReshantaGathering(Model):
    source: str
    points: list[Coordinate] = Field(max_length=1000)
