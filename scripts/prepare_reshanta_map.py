# SPDX-License-Identifier: GPL-3.0-only
"""Assemble the pinned Lower Reshanta tiles supplied by the user into a local PNG."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tiles', type=Path, help='Directory containing the 16 original WebP files')
    parser.add_argument('output', type=Path, help='Destination PNG to import in Siege Command')
    args = parser.parse_args()
    manifest_path = Path(__file__).resolve().parents[1] / 'data-sources/siege-reshanta.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    frame = np.empty((4096, 4096, 3), dtype=np.uint8)
    for name, expected in manifest['tile_sha256'].items():
        column, row = map(int, name.split('_'))
        tile_path = args.tiles / f'Abyss_Reshanta_A_{column:02d}_{row:02d}.webp'
        raw = tile_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            parser.error(f'Tile differs from the calibrated source: {tile_path.name}')
        tile = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
        if tile is None or tile.shape != (1024, 1024, 3):
            parser.error(f'Could not decode tile: {tile_path.name}')
        frame[row*1024:(row+1)*1024, column*1024:(column+1)*1024] = tile
    if hashlib.sha256(frame).hexdigest() != manifest['map_pixels_sha256']:
        parser.error('The assembled image does not match the calibrated source.')
    ok, encoded = cv2.imencode('.png', frame)
    if not ok:
        parser.error('Could not encode the PNG.')
    args.output.write_bytes(encoded.tobytes())
    print(args.output.resolve())


if __name__ == '__main__':
    main()
