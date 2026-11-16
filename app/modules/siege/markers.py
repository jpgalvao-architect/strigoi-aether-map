# SPDX-License-Identifier: GPL-3.0-only
"""Siege preset layers in the live overlay's normalized marker format."""
from app.modules.overlay.badges import Badge
from app.modules.siege.models import COLORS, MAP_ID, OBJECTIVE_CATEGORY


def badge_for(layer, caption, scale, *, selected=False, provisional=False):
    ring = layer in {'SiegeRings', 'TransitRings'}
    priority = {'SiegeObjectives': 4, 'CustomMarkers': 4, 'SiegeRings': 3, 'TransitRings': 2}.get(layer, 1)
    return Badge(caption, scale, selected=selected, provisional=provisional,
                 ring=ring, priority=priority, size=10. if priority >= 2 else 4.5)


def pin_layer(marker):
    return 'SiegeObjectives' if marker.category == OBJECTIVE_CATEGORY else 'CustomMarkers'


def pin_color(marker, preset):
    layer = pin_layer(marker)
    return marker.color or preset.colors.get(layer, COLORS[layer])


def pin_visible(marker, preset):
    return marker.visible and pin_layer(marker) in preset.layers


def pin_badge(marker, preset, *, selected=False):
    caption = marker.name if len(marker.name) <= 12 else marker.name[:11] + '…'
    return badge_for(pin_layer(marker), caption, preset.marker_scale * marker.scale, selected=selected)


def markers_for(siege, dataset, *, tactical=True, exploration=True, shared=None):
    local = siege.preset
    preset = shared if shared is not None else local
    colors = COLORS | preset.colors

    def badge(position, layer, caption, *, provisional=False):
        return (position.x, position.y, colors[layer],
                badge_for(layer, caption, preset.marker_scale, provisional=provisional))

    markers = []
    if exploration and local.layers & {'Pets', 'Gathering'}:
        local_colors = COLORS | local.colors
        resources = {resource.id: resource for resource in dataset.resources}
        for point in dataset.points:
            if point.map_id == MAP_ID and point.enabled:
                layer = 'Pets' if resources[point.resource_id].category == 'pets' else 'Gathering'
                if layer in local.layers:
                    markers.append((point.x, point.y, local_colors[layer], badge_for(layer, '', local.marker_scale)))
    if not tactical:
        return markers
    markers.extend((marker.position.x, marker.position.y, pin_color(marker, preset), pin_badge(marker, preset))
                   for marker in preset.markers if pin_visible(marker, preset))
    for ring, position, code in siege.display_rings(preset, shared=shared is not None):
        layer = 'SiegeRings' if ring.category == 'siege' else 'TransitRings'
        if layer not in preset.layers:
            continue
        if position is not None:
            markers.append(badge(position.map_position, layer, code or '?',
                                 provisional=position.status == 'provisional'))
    markers.sort(key=lambda marker: marker[3].priority)
    return markers
