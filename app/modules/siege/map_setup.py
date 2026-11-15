# SPDX-License-Identifier: GPL-3.0-only
"""Prepare the pinned Lower Reshanta map from its publicly hosted tiles."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.request import urlopen

import cv2
import numpy as np

from app.infrastructure.storage import PACKAGE

MANIFEST = PACKAGE.parent / 'data-sources' / 'siege-reshanta.json'
LOCAL_MAP = 'siege-reshanta.png'
PREPARED_MAP = 'reshanta-base.png'
MAP_SIZE = 4096
MAP_PIXELS_SHA256 = '4fd42390453a4baa4dd4f9a02e5fb3c4263d0a15ebc03b159e6b60fb08d00d57'
REPOSITORY = 'aion2-interactive-map/aion2-interactive-map'
MAP_TREE = 'public/UI/Map/WorldMap/Abyss_Reshanta_A'
MAP_COMMIT = '89ce3984d569ff1a03ee6311d064231211212981'
MAP_SOURCE = f'https://github.com/{REPOSITORY}/tree/{MAP_COMMIT}/{MAP_TREE}'
MAX_TILE_BYTES = 2_000_000


def validate_map(path):
    if not 0 < path.stat().st_size <= 32_000_000:
        raise ValueError('A imagem do mapa deve ter até 32 MB.')
    raw = path.read_bytes()
    if raw[:8] != b'\x89PNG\r\n\x1a\n' or raw[12:24] != b'IHDR\x00\x00\x10\x00\x00\x00\x10\x00':
        raise ValueError('Use o PNG de Lower Reshanta no quadro calibrado de 4096 × 4096.')
    pixels = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if pixels is None or hashlib.sha256(pixels).hexdigest() != MAP_PIXELS_SHA256:
        raise ValueError('A imagem local de Reshanta não corresponde à base calibrada.')
    return raw


def write_map(destination, raw):
    fd, temporary = tempfile.mkstemp(prefix='siege-map-', dir=destination.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def download_tile(column, row, expected):
    url = (f'https://raw.githubusercontent.com/{REPOSITORY}/{MAP_COMMIT}/{MAP_TREE}/Res/'
           f'Abyss_Reshanta_A_{column:02d}_{row:02d}.webp')
    with urlopen(url, timeout=10) as response:
        raw = response.read(MAX_TILE_BYTES+1)
    if len(raw) > MAX_TILE_BYTES or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f'Arquivo do mapa alterado ({column}, {row}).')
    pixels = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if pixels is None or pixels.shape != (1024, 1024, 3):
        raise ValueError(f'Arquivo do mapa inválido ({column}, {row}).')
    return column, row, pixels


def prepare_map(directory):
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / PREPARED_MAP
    for path in (directory / LOCAL_MAP, destination):
        try:
            validate_map(path)
        except (OSError, ValueError):
            continue
        return path

    hashes = json.loads(MANIFEST.read_text(encoding='utf-8'))['tile_sha256']
    tiles = np.empty((MAP_SIZE, MAP_SIZE, 3), dtype=np.uint8)
    with ThreadPoolExecutor(max_workers=4) as pool:
        downloads = [pool.submit(download_tile, col, row, hashes[f'{col}_{row}'])
                     for row in range(4) for col in range(4)]
        for download in downloads:
            col, row, pixels = download.result()
            tiles[row*1024:(row+1)*1024, col*1024:(col+1)*1024] = pixels
    if hashlib.sha256(tiles).hexdigest() != MAP_PIXELS_SHA256:
        raise ValueError('O mosaico recebido não corresponde ao mapa calibrado.')
    ok, image = cv2.imencode('.png', tiles)
    if not ok:
        raise OSError('Falha ao gravar o mapa de Lower Reshanta.')
    write_map(destination, image.tobytes())
    return destination
