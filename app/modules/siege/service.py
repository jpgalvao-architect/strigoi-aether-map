# SPDX-License-Identifier: GPL-3.0-only
"""Owns validated local settings and emits tactical state without UI dependencies."""
import json
import logging
import re
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QObject, Signal

from pydantic import Field

from app.core.models import Category, Gatherable, MapDefinition, Model, PointOfInterest, Region, Subcategory
from app.infrastructure.storage import PACKAGE, atomic_json, load_model, recover_model
from app.modules.siege.map_setup import LOCAL_MAP, MAP_SIZE, MAP_SOURCE, PREPARED_MAP, validate_map, write_map
from app.modules.siege.models import (
    COLORS, LEGACY_OFFICIAL, MAP_ID, OBJECTIVE_CATEGORY, OFFICIAL, PREFIX, SECTORS,
    CalibratedRing, Cartography, Coordinate, CustomMarker,
    Preset, RingCatalogue, RingPosition, SiegeState, TacticalCall, TacticalDrawing,
)
from app.modules.siege.transit_codes import TRANSIT_CODES

RING_SOURCE = 'https://metabot.gg/en/aion-2/map/chaotic-lower-reshanta/flight-rings'
ACTIONS = {'regroup': 'REAGRUPAR', 'attack': 'ATACAR', 'defend': 'DEFENDER', 'retreat': 'RECUAR'}


class SiegeService(QObject):
    changed = Signal()
    map_changed = Signal()
    session_changed = Signal()
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
        self.catalogue = {ring.ring_id: ring for ring in catalogue.rings}
        self.official_rings = {ring.ring_id: ring for ring in original.rings}
        self.session_preset = None
        self.objectives = {objective.number: objective for objective in self.data.objectives}
        self.state, self.warning = recover_model(self.path, SiegeState, SiegeState())
        self.warning = self.warning or catalogue_warning
        self._migrate_state()
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
        active = {key: ring for key, ring in self.catalogue.items() if not key.startswith('ring-pending-')}
        for ring in incoming.rings:
            previous = active.get(ring.ring_id)
            if previous is not None and (previous.default_callsign != ring.default_callsign
                                         or previous.sector != ring.sector):
                raise ValueError('O catálogo não pode trocar o callsign ou setor já fixado de um anel.')
            active[ring.ring_id] = ring
        official = {ring.default_callsign: ring.ring_id for ring in active.values() if ring.default_callsign}
        portable = ((ring.ring_id, ring.default_callsign) for preset in self.state.presets
                    for ring in preset.calibrated_rings if ring.default_callsign)
        local = self.state.local_callsigns.items()
        if any(code in official and official[code] != ring_id for ring_id, code in (*local, *portable)):
            raise ValueError('O catálogo conflita com um callsign local já fixado.')
        complete = RingCatalogue(map_frame=incoming.map_frame, rings=list(active.values()))
        atomic_json(self.ring_path, complete)
        self.catalogue = active
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

    def standard_markers(self):
        return [
            CustomMarker(id=f'objective-{objective.code.lower()}', name=objective.code,
                         category=OBJECTIVE_CATEGORY, origin='default',
                         position=objective.map_position.model_copy())
            for objective in sorted(self.objectives.values(), key=lambda objective: objective.number)
        ]

    def default_preset(self, name=OFFICIAL):
        return Preset(name=name, layers={'SiegeObjectives', 'SiegeRings', 'TransitRings', 'CustomMarkers'},
                      markers=self.standard_markers())

    def _upgrade_preset(self, preset):
        if preset.schema_version == 3:
            return preset
        markers = preset.markers
        if preset.schema_version == 1:
            existing = {marker.id for marker in markers}
            markers = [*(marker for marker in self.standard_markers() if marker.id not in existing), *markers]
        return Preset.model_validate({**preset.model_dump(), 'schema_version': 3, 'markers': markers})

    def _migrate_state(self):
        previous = self.state
        presets = [self._upgrade_preset(preset) for preset in previous.presets]
        official = next((preset for preset in presets if preset.name.strip().casefold() == OFFICIAL.casefold()), None)
        if official is None:
            official = self.default_preset()
            presets.insert(0, official)
        selected = previous.selected_preset
        if selected == LEGACY_OFFICIAL or selected not in {preset.name for preset in presets}:
            selected = official.name
        self.state = SiegeState.model_validate({
            **previous.model_dump(), 'schema_version': 3, 'presets': presets, 'selected_preset': selected,
        })
        if self.path.is_file() and previous != self.state:
            try:
                atomic_json(self.path, self.state)
            except OSError:
                logging.getLogger(__name__).exception('Falha ao gravar a migração dos presets de siege')
                self.warning = self.warning or 'Não foi possível salvar a migração das marcações.'

    @property
    def preset(self):
        return next(preset for preset in self.state.presets if preset.name == self.state.selected_preset)

    @property
    def rings(self):
        return self.rings_for(self.state)

    def rings_for(self, state):
        preset = next(p for p in state.presets if p.name == state.selected_preset)
        if not preset.use_local_calibration or not preset.calibrated_rings:
            return self.catalogue
        imported = {ring.ring_id: ring for ring in preset.calibrated_rings}
        return imported | self.catalogue

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
        if name != self.state.selected_preset:
            if not any(preset.name == name for preset in self.state.presets):
                raise ValueError('Preset não encontrado.')
            self._commit(selected_preset=name)

    def save_preset(self, preset, *, replace=True):
        preset = self._upgrade_preset(preset)
        name = preset.name.strip()
        if not name or not name.isprintable():
            raise ValueError('Nome do preset inválido.')
        if name != preset.name:
            preset = preset.model_copy(update={'name': name})
        presets = list(self.state.presets)
        key = name.casefold()
        index = next((i for i, existing in enumerate(presets) if existing.name.strip().casefold() == key), None)
        if index is None:
            presets.append(preset)
        elif not replace:
            raise ValueError('Já existe um preset com este nome.')
        else:
            presets[index] = preset
        self._commit(presets=presets, selected_preset=name)

    def create_preset(self, name):
        self.save_preset(self.default_preset(name), replace=False)

    def edit_preset(self, **changes):
        self.save_preset(Preset.model_validate({**self.preset.model_dump(), **changes}))

    def restore_standard_markers(self):
        defaults = self.standard_markers()
        ids = {marker.id for marker in defaults}
        extras = [marker for marker in self.preset.markers if marker.id not in ids]
        self.edit_preset(markers=[*defaults, *extras], layers=self.preset.layers | {'SiegeObjectives'})

    def available_name(self, name):
        used = {p.name.strip().casefold() for p in self.state.presets}
        candidate = name
        suffix = 2
        while candidate.casefold() in used:
            ending = f' ({suffix})'
            candidate = name[:70-len(ending)].rstrip() + ending
            suffix += 1
        return candidate

    def read_preset(self, path):
        maximum = 5_000_000
        with path.open('rb') as stream:
            payload = stream.read(maximum + 1)
        if len(payload) > maximum:
            raise ValueError('O arquivo de marcações é grande demais.')
        try:
            data = json.loads(payload)
            if not isinstance(data, dict) or not {'schema_version', 'map_id'} <= data.keys():
                raise ValueError('Cabeçalho de marcações incompleto.')
            if data['schema_version'] in (2, 3) and 'markers' not in data:
                raise ValueError('Lista de marcações ausente.')
            if data['schema_version'] == 3 and 'drawings' not in data:
                raise ValueError('Lista de formas ausente.')
            return self._upgrade_preset(Preset.model_validate(data))
        except (ValueError, RecursionError) as error:
            raise ValueError('JSON de marcações inválido. Confira a versão, o mapa, os IDs e as coordenadas.') from error

    def import_preset(self, path, *, replace=False):
        self.accept_preset(self.read_preset(path), replace=replace)

    def accept_preset(self, preset, *, replace=False):
        name = preset.name.strip()
        numbered = {ring.default_callsign: ring.ring_id for ring in self.catalogue.values() if ring.default_callsign}
        numbered.update({code: ring_id for ring_id, code in self.state.local_callsigns.items()})
        for ring in preset.calibrated_rings:
            known = self.catalogue.get(ring.ring_id)
            if ((known is not None and known.sector != ring.sector)
                    or numbered.get(ring.default_callsign, ring.ring_id) != ring.ring_id):
                raise ValueError('A calibração importada conflita com um anel ou código local.')
        if replace:
            name = self.preset.name
        elif name:
            name = self.available_name(name)
        self.save_preset(preset.model_copy(update={'name': name}), replace=replace)

    def set_session_preset(self, preset):
        if preset != self.session_preset:
            self.session_preset = preset
            self.session_changed.emit()

    def display_rings(self, preset, *, shared=False):
        if not shared:
            return ((ring, self.position(ring), self.ring_code(ring)) for ring in self.rings.values())
        rings = self.official_rings
        if preset.use_local_calibration:
            rings = rings | {ring.ring_id: ring for ring in preset.calibrated_rings}
        return (
            (ring, ring.position, TRANSIT_CODES.get(ring.ring_id) if ring.category == 'transit' else ring.default_callsign)
            for ring in rings.values()
        )

    def exportable_preset(self):
        preset = self.preset
        if preset.use_local_calibration:
            calibrated = {ring.ring_id: self.portable_ring(ring, ring.position) for ring in preset.calibrated_rings}
            for ring_id, position in self.state.local_rings.items():
                ring = self.catalogue.get(ring_id)
                if ring is not None and ring_id not in calibrated:
                    calibrated[ring_id] = self.portable_ring(ring, position)
            preset = Preset.model_validate({**preset.model_dump(), 'calibrated_rings': list(calibrated.values())})
        return preset

    def export_preset(self, path):
        atomic_json(path, self.exportable_preset())

    def portable_ring(self, ring, position):
        official = self.catalogue.get(ring.ring_id) or ring
        code = ring.default_callsign or official.default_callsign or self.state.local_callsigns.get(ring.ring_id)
        if not ring.sector or not code or not code.startswith(PREFIX[ring.sector]):
            code = None
        return CalibratedRing.model_validate({
            **ring.model_dump(), 'position': position, 'source': position.source,
            'geographic_description': '', 'default_callsign': code,
        })

    def add_marker(self, name, position):
        marker = CustomMarker(id=f'local-{uuid4().hex}', name=name, position=position)
        self.edit_preset(markers=[*self.preset.markers, marker], layers=self.preset.layers | {'CustomMarkers'})
        return marker

    def edit_marker(self, marker_id, **changes):
        if {'id', 'origin'} & changes.keys():
            raise ValueError('A identidade do pin é permanente.')
        markers = self.preset.markers
        if not any(marker.id == marker_id for marker in markers):
            raise ValueError('Pin não encontrado.')
        self.edit_preset(markers=[
            CustomMarker.model_validate({**marker.model_dump(), **changes}) if marker.id == marker_id else marker
            for marker in markers
        ])

    def delete_marker(self, marker_id):
        self.edit_preset(markers=[marker for marker in self.preset.markers if marker.id != marker_id])

    def add_drawing(self, kind, start, end, **style):
        defaults = {'stroke': 'solid'} if kind == 'arrow' else {}
        drawing = TacticalDrawing(id=f'shape-{uuid4().hex}', kind=kind, start=start, end=end, **(defaults | style))
        self.edit_preset(drawings=[*self.preset.drawings, drawing], layers=self.preset.layers | {'TacticalShapes'})
        return drawing

    def edit_drawing(self, drawing_id, **changes):
        drawing = next((drawing for drawing in self.preset.drawings if drawing.id == drawing_id), None)
        if drawing is None or 'id' in changes:
            raise ValueError('Forma tática não encontrada.')
        replacement = TacticalDrawing.model_validate({**drawing.model_dump(), **changes})
        if replacement != drawing:
            self.edit_preset(drawings=[replacement if item.id == drawing_id else item
                                       for item in self.preset.drawings])

    def delete_drawing(self, drawing_id):
        self.edit_preset(drawings=[drawing for drawing in self.preset.drawings if drawing.id != drawing_id])

    def _clear_unusable_call(self, state):
        call = state.tactical_call
        changes = {}
        if call.ring_id:
            ring = self.rings_for(state).get(call.ring_id)
            if not ring or ring.sector != call.sector or not self.callsign(ring, state=state):
                changes['ring_id'] = None
        if call.objective and self.objectives[call.objective].sector != call.sector:
            changes['objective'] = None
        if changes:
            state.tactical_call = call.model_copy(update=changes)

    def position(self, ring, *, state=None):
        state = self.state if state is None else state
        preset = next((p for p in state.presets if p.name == state.selected_preset), None)
        if preset and preset.use_local_calibration:
            imported = next((r for r in preset.calibrated_rings if r.ring_id == ring.ring_id), None)
            if imported is not None:
                return imported.position
            return state.local_rings.get(ring.ring_id) or ring.position
        return ring.position

    def local_position(self, ring_id):
        imported = next((ring for ring in self.preset.calibrated_rings if ring.ring_id == ring_id), None)
        return imported.position if imported is not None else self.state.local_rings.get(ring_id)

    def callsign(self, ring, *, state=None):
        state = self.state if state is None else state
        position = self.position(ring, state=state)
        if position is None or position.status != 'verified':
            return None
        if ring.default_callsign:
            return ring.default_callsign
        preset = next(p for p in state.presets if p.name == state.selected_preset)
        imported_code = next((r.default_callsign for r in preset.calibrated_rings if r.ring_id == ring.ring_id), None)
        code = (imported_code if preset.use_local_calibration else None) or state.local_callsigns.get(ring.ring_id, '')
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
        calibrated = self.preset.calibrated_rings
        if any(ring.ring_id == ring_id for ring in calibrated):
            self.edit_preset(calibrated_rings=[
                self.portable_ring(ring, position) if ring.ring_id == ring_id else ring for ring in calibrated
            ])
        else:
            self._commit(local_rings={**self.state.local_rings, ring_id: position})

    def reset_ring(self, ring_id):
        calibrated = self.preset.calibrated_rings
        if any(ring.ring_id == ring_id for ring in calibrated):
            self.edit_preset(calibrated_rings=[ring for ring in calibrated if ring.ring_id != ring_id])
        elif ring_id in self.state.local_rings:
            local = dict(self.state.local_rings)
            del local[ring_id]
            self._commit(local_rings=local)

    def freeze_callsigns(self, sector):
        prefix = PREFIX[sector]
        codes = dict(self.state.local_callsigns)
        imported = {r.ring_id: r.default_callsign for r in self.preset.calibrated_rings if r.default_callsign}
        used = [r.default_callsign for r in self.rings.values() if r.default_callsign]
        used.extend(codes.values())
        used.extend(imported.values())
        latest = max((int(c[1:]) for c in used if re.fullmatch(prefix + r'[1-9][0-9]*', c)), default=0)
        eligible = [r for r in self.rings.values() if r.sector == sector and not r.default_callsign
                    and r.ring_id not in codes and r.ring_id not in imported
                    and (position := self.local_position(r.ring_id) or r.position)
                    and position.status == 'verified']
        # 8 px bands on the canonical frame. Within a band, west comes first.
        def order(ring):
            position = self.local_position(ring.ring_id) or ring.position
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
