# SPDX-License-Identifier: GPL-3.0-only
"""Derive only supplied up/down levels, preserving source coordinates and IDs."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
provenance = json.loads((root/'app/data/cube-sites-provenance.json').read_text(encoding='utf-8'))
levels = {}
for map_id in ('altgard', 'verteron'):
    path = root/f'data-sources/object-sets/{map_id}.json'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == provenance['files'][path.name]
    data = json.loads(path.read_text(encoding='utf-8'))
    for node in data['nodes']:
        if node['categoryId'] != f'hidden-cube-{map_id}' or node.get('level') not in ('up', 'down'):
            continue
        levels[f'spawn-{map_id}-{node["id"]}'] = dict(map_id=map_id, x=node['x']/100,
            y=node['y']/100, level=node['level'])
result = dict(source=provenance['source'], commit=provenance['commit'], license=provenance['license'],
              semantics=provenance['height'], levels=levels)
(root/'app/data/cube-height-levels.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
print('Source-provided height flags:', len(levels))
