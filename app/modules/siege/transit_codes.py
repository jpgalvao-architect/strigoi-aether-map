# SPDX-License-Identifier: GPL-3.0-only
"""Stable callsigns by source ID, grouped using the Lower Reshanta game map."""

# Within each group, number north to south, west first in the same 8 px band.
# Keep the numbering fixed when a catalogue is partial or locally recalibrated.
TRANSIT_GROUPS = {
    'BF': (294009, 294932, 293952, 293910, 294237, 295872, 295373, 295427, 294022, 295450),
    'DR': (295321, 295248, 294565, 295063, 294171, 294507, 293834, 295186),
    'LR': (295313, 293726, 294620, 295252, 293832, 294785, 293953, 295161, 295519, 295790),
    'ER': (295279,),
    'WR': (293719,),
}

TRANSIT_CODES = {
    f'ring-reshanta-{source_id}': f'{prefix}{number}'
    for prefix, group in TRANSIT_GROUPS.items()
    for number, source_id in enumerate(group, 1)
}
