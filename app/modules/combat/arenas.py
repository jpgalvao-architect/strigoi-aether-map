# SPDX-License-Identifier: GPL-3.0-only
"""SA arenas observed on 2026-10-13; map rotation coverage is incomplete.

The timer's first field differs from the zone's map ID in these observations.
Allow that association only for an observed pair, never an inferred ID range.
"""

# ZoneChangedEvent.MapId -> (mode, InstanceTimerEvent.MapId).
OBSERVED_ARENAS = {61: ("1v1", 8), 60: ("5v5", 7)}


def arena_mode(map_id):
    return OBSERVED_ARENAS.get(map_id, (None, None))[0]


def timer_matches_map(map_id, timer_id):
    return timer_id == map_id or (
        map_id in OBSERVED_ARENAS and timer_id == OBSERVED_ARENAS[map_id][1]
    )
