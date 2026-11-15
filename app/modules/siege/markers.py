# SPDX-License-Identifier: GPL-3.0-only
"""Siege preset layers in the live overlay's normalized marker format."""
from app.modules.overlay.badges import Badge
from app.modules.siege.models import COLORS, MAP_ID


def badge_for(layer, caption, scale, *, selected=False, provisional=False):
    ring = layer in {'SiegeRings', 'TransitRings'}
    priority = {'SiegeObjectives': 4, 'CustomMarkers': 4, 'SiegeRings': 3, 'TransitRings': 2}.get(layer, 1)
    objective = layer == 'SiegeObjectives'
    size = 12. if objective else 10. if priority >= 2 else 4.5
    return Badge(caption, scale, selected=selected, provisional=provisional,
                 ring=ring, priority=priority, size=size, pin_code=objective)


def markers_for(siege, dataset):
    preset, call = siege.preset, siege.call
    colors = COLORS | preset.colors

    def badge(position, layer, caption, *, selected=False, provisional=False):
        return (position.x, position.y, colors[layer],
                badge_for(layer, caption, preset.marker_scale, selected=selected, provisional=provisional))

    markers = []
    if preset.layers & {'Pets', 'Gathering'}:
        resources = {resource.id: resource for resource in dataset.resources}
        for point in dataset.points:
            if point.map_id == MAP_ID and point.enabled:
                layer = 'Pets' if resources[point.resource_id].category == 'pets' else 'Gathering'
                if layer in preset.layers:
                    markers.append((point.x, point.y, colors[layer], badge_for(layer, '', preset.marker_scale)))
    if 'CustomMarkers' in preset.layers:
        markers.extend(badge(marker.position, 'CustomMarkers', marker.name[:4]) for marker in preset.markers)
    for ring in siege.rings.values():
        layer = 'SiegeRings' if ring.category == 'siege' else 'TransitRings'
        if layer not in preset.layers:
            continue
        position = siege.position(ring)
        if position is not None:
            provisional = position.status == 'provisional'
            markers.append(badge(position.map_position, layer, siege.ring_code(ring) or '?',
                                 selected=call.ring_id == ring.ring_id, provisional=provisional))
    if 'SiegeObjectives' in preset.layers:
        markers.extend(badge(objective.map_position, 'SiegeObjectives', objective.code,
                             selected=call.objective == objective.number, provisional=objective.status != 'verified')
                       for objective in siege.objectives.values())
    # Keep the current tactical call above neighboring points.
    markers.sort(key=lambda marker: (marker[3].selected, marker[3].priority))
    return markers
