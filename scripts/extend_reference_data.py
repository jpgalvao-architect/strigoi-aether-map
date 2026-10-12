# SPDX-License-Identifier: GPL-3.0-only
"""Adapt separately licensed object sets; retain historical cube identities."""
import hashlib
import json
from pathlib import Path
import sys
import re

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.core.models import Dataset
COMMIT='a23dc90849fd18b1ef4fba01d2f1bb0f851bdcbd'
SOURCE=f'https://github.com/problem-xyz/aion2-map-overlay/blob/{COMMIT}/assets/object-sets/'
path=ROOT/'app/data/dataset.json'
data=json.loads(path.read_text(encoding='utf-8'))
data['points']=[p for p in data['points'] if not p['id'].startswith('gather-')]
resources={r['id']:r for r in data['resources']}
history=json.loads((ROOT/'app/data/coordinate-corrections.json').read_text(encoding='utf-8'))
for record in history['corrections']:
    data['cubes']=[record['original'] if p==record['replacement'] else p for p in data['cubes']]
data['cubes']=[p for p in data['cubes'] if not p['id'].startswith('spawn-')]
previous_manifest=ROOT/'app/data/cube-sites-provenance.json'
previous=json.loads(previous_manifest.read_text(encoding='utf-8')) if previous_manifest.exists() else {}
legacy_resource=previous.get('legacy_resource',dict(resources['cubes']))
resources['cubes']['name']='Cubos • registros antigos KR/TW'
resources['cubes']['verification']='Base histórica KR/TW; sem confirmação individual em SA'
resources['cube-spawns']=dict(id='cube-spawns',name='Cubos • posições possíveis',category='cubes',subcategory='cubes',
    rarity='unknown',source=SOURCE,verification='Locais possíveis de aparecimento; versão regional da fonte não declarada; SA não validado individualmente',
    notes='Cada grupo reúne posições possíveis, não cubos presentes simultaneamente. Altura relativa da fonte; uso não comercial CC BY-NC 4.0.')
counts={}
cube_counts={}
for map_id in ['altgard','verteron']:
    original=ROOT/f'data-sources/object-sets/{map_id}.json'
    obj=json.loads(original.read_text(encoding='utf-8'))
    cube_nodes=[n for n in obj['nodes'] if n['categoryId']=='hidden-cube-'+map_id]
    cube_counts[map_id]=len(cube_nodes)
    for node in cube_nodes:
        group,spot=node['id'].removeprefix('cube-').rsplit('-',1)
        location=re.sub(r'(?<=[a-z])(?=[A-Z])',' ',group.split('_')[0])
        height={'up':'Acima da altura mediana do grupo na fonte.', 'down':'Abaixo da altura mediana do grupo na fonte.'}.get(node.get('level'),'Altura relativa não informada.')
        data['cubes'].append(dict(id=f'spawn-{map_id}-{node["id"]}',name=f'Hidden Cube · {location} · posição {spot}',
            map_id=map_id,resource_id='cube-spawns',x=node['x']/100,y=node['y']/100,certainty='possible',
            source=SOURCE+map_id+'.json',underwater=None,visible_in_overlay=True,
            notes=f'Posição possível de aparecimento. Grupo: {group}; posição: {spot}. {height} Região/versão do cliente não declarada pela fonte; validar em SA.',
            route_hint='A presença do cubo, o acesso e a condição subaquática precisam de confirmação no jogo.'))
    selected=[n for n in obj['nodes'] if n['categoryId'].startswith('gathering-')]
    counts[map_id]=len(selected)
    for node in selected:
        resource=node['categoryId'].removeprefix('gathering-')
        if resource not in resources:
            raise ValueError(resource)
        data['points'].append(dict(id='gather-'+node['id'],name=node['title'],map_id=map_id,
            resource_id=resource,x=node['x']/100,y=node['y']/100,
            source=SOURCE+map_id+'.json',certainty='possible',visible_in_overlay=True,
            notes='Base comunitária compartilhada. Ponto de coleta sem confirmação individual em SA.'))
        resources[resource]['source']=SOURCE+map_id+'.json'
        resources[resource]['verification']='Nome catalogado e posições publicadas; confirmar no servidor SA'
        resources[resource]['notes']='Coordenadas da distribuição problem-xyz / tc-imba, CC BY-NC 4.0. Raridade não informada.'
for point in data['points']+data['cubes']:
    point['visible_in_overlay']=True
for m in data['maps']:
    m['supports_overlay']=True
    m['name']=('Altgard' if m['id']=='altgard' else 'Verteron')+' • base compartilhada'
data['resources']=list(resources.values())
data['release']='cube-sites-v050'
data['coverage']='Agenda SA selecionável • cubos: posições possíveis da fonte comunitária, sem validação individual em SA'
data=Dataset.model_validate(data).model_dump(mode='json')
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest=dict(commit=COMMIT,source=SOURCE,license='CC BY-NC 4.0',author='Yihao Liu (tc-imba), colaboradores e adaptação problem-xyz',
    counts=counts,changes='Apenas pontos de coleta; x e y percentuais divididos por 100; IDs com prefixo gather-; sem inversão adicional de Y.',
    sa_exclusive=False,files={f'{name}.json':hashlib.sha256((ROOT/f'data-sources/object-sets/{name}.json').read_bytes()).hexdigest() for name in counts})
(ROOT/'app/data/gathering-provenance.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
cube_manifest=dict(release='cube-sites-v050',checked_on='2026-10-12',commit=COMMIT,source=SOURCE,license='CC BY-NC 4.0',
    counts=cube_counts,legacy_counts=dict(altgard=108,verteron=118),legacy_resource=legacy_resource,
    maps=data['maps'],files=manifest['files'],sa_exclusive=False,sa_individually_validated=False,
    regional_client_version='Não declarada na fonte',
    semantics='Todos os locais possíveis de aparecimento por grupo; não representam presença simultânea.',
    transformation='x/100, y/100; origem superior esquerda; nenhuma inversão adicional de Y.',
    identity='spawn-{map_id}-{node_id}; IDs antigos e visitas mantidos em camada histórica separada.',
    height='level up/down indica altura relativa à mediana do grupo; não confirma condição subaquática.')
(ROOT/'app/data/cube-sites-provenance.json').write_text(json.dumps(cube_manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'{sum(cube_counts.values())} posições possíveis de cubos; 226 registros históricos separados.')
print(f'{sum(counts.values())} pontos de coleta adicionados; total {len(data["points"])+len(data["cubes"])}. JSON: {path.stat().st_size} bytes')
