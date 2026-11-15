# SPDX-License-Identifier: GPL-3.0-only
"""Siege preset layers in the live overlay's normalized marker format."""
from app.modules.overlay.badges import Badge
from app.modules.siege.models import COLORS, MAP_ID


def markers_for(siege, dataset):
    preset, call = siege.preset, siege.call
    colors = COLORS | preset.colors

    def badge(position, layer, caption, *, selected=False, provisional=False):
        return (position.x, position.y, colors[layer],
                Badge(caption, preset.marker_scale, selected, provisional))

    markers = []
    if preset.layers & {'Pets', 'Gathering'}:
        resources = {resource.id: resource for resource in dataset.resources}
        for point in dataset.points:
            if point.map_id == MAP_ID and point.enabled:
                layer = 'Pets' if resources[point.resource_id].category == 'pets' else 'Gathering'
                if layer in preset.layers:
                    markers.append((point.x, point.y, colors[layer], 'circle'))
    if 'CustomMarkers' in preset.layers:
        markers.extend(badge(marker.position, 'CustomMarkers', marker.name[:4]) for marker in preset.markers)
    for ring in siege.rings.values():
        layer = 'SiegeRings' if ring.category == 'siege' else 'TransitRings'
        if layer not in preset.layers:
            continue
        position = siege.position(ring)
        if position is not None:
            provisional = position.status == 'provisional'
            markers.append(badge(position.map_position, layer, siege.callsign(ring) or ('?' if provisional else '○'),
                                 selected=call.ring_id == ring.ring_id, provisional=provisional))
    if 'SiegeObjectives' in preset.layers:
        markers.extend(badge(objective.map_position, 'SiegeObjectives', objective.code,
                             selected=call.objective == objective.number, provisional=objective.status != 'verified')
                       for objective in siege.objectives.values())
    # Keep the current tactical call above neighboring points.
    markers.sort(key=lambda marker: isinstance(marker[3], Badge) and marker[3].selected)
    return markers
