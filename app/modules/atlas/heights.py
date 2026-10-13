# SPDX-License-Identifier: GPL-3.0-only
"""Source-relative spawn heights; no inference from the player's altitude."""
from functools import lru_cache
import json
from app.infrastructure.storage import PACKAGE


@lru_cache(maxsize=1)
def height_levels():
    return json.loads((PACKAGE/'data/cube-height-levels.json').read_text(encoding='utf-8'))['levels']


def point_marker_shape(point, shape):
    if shape != 'cube' or point.resource_id != 'cube-spawns':
        return shape
    record = height_levels().get(point.id)
    if (record and record['map_id'] == point.map_id and abs(record['x']-point.x) < 1e-10
            and abs(record['y']-point.y) < 1e-10 and record['level'] in ('up', 'down')):
        return 'cube-' + record['level']
    return shape  # Missing or edited coordinates never receive an invented height.
