# SPDX-License-Identifier: GPL-3.0-only
"""Selective cube-site migration; never transfer identities by proximity."""
from app.core.models import Gatherable, HiddenCube, MapDefinition


def upgrade_cube_sites(dataset, bundled, provenance, history):
    if dataset.release not in ('sa-live-overlay-v030', 'cube-sites-v050'):
        return dataset, []
    maps = {m.id: m for m in dataset.maps}
    eligible = {m['id'] for m in provenance['maps']
                if maps.get(m['id']) == MapDefinition.model_validate(m)}
    if not eligible:
        return dataset, []
    result = dataset.model_copy(deep=True)
    changes = []
    # Withdraw only the exact unedited v0.4.2 replacement.
    for record in history['corrections']:
        replacement = HiddenCube.model_validate(record['replacement'])
        if replacement.map_id not in eligible:
            continue
        for index, cube in enumerate(result.cubes):
            if cube == replacement:
                result.cubes[index] = HiddenCube.model_validate(record['original'])
                changes.append(cube.id)
    resources = {r.id: r for r in result.resources}
    target = next(r for r in bundled.resources if r.id == 'cube-spawns')
    if 'cube-spawns' not in resources:
        result.resources.append(target.model_copy(deep=True))
        resources[target.id] = target
        changes.append(target.id)
    # A custom conflicting resource is not assigned bundled coordinates.
    if resources['cube-spawns'] == target:
        existing = {p.id for p in result.all_points}
        additions = [p.model_copy(deep=True) for p in bundled.cubes
                     if p.resource_id == target.id and p.map_id in eligible and p.id not in existing]
        result.cubes.extend(additions)
        changes.extend(p.id for p in additions)
    original_resource = Gatherable.model_validate(provenance['legacy_resource'])
    if resources.get('cubes') == original_resource:
        renamed = next(r for r in bundled.resources if r.id == 'cubes')
        result.resources = [renamed.model_copy(deep=True) if r.id == 'cubes' else r for r in result.resources]
        changes.append('cubes')
    old_coverage = 'SA / Agenda regional selecionável • mapa e pontos comunitários compartilhados, a confirmar no jogo'
    if changes:
        result.release = bundled.release
        if result.coverage == old_coverage:
            result.coverage = bundled.coverage
        return result, changes
    return dataset, []
