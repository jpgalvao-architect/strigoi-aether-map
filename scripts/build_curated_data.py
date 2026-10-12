# SPDX-License-Identifier: GPL-3.0-only
"""Rebuild the pinned community atlas. Development only: requires PyYAML.

No game client access or scraping. Input YAML is distributed under CC BY-NC 4.0.
The generated SVG is a coordinate diagram of the supplied region polygons.
"""
from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data-sources/community'
COMMIT = '89ce3984d569ff1a03ee6311d064231211212981'
URL = 'https://github.com/aion2-interactive-map/aion2-interactive-map'
CHECKED = '2026-10-11'
RELEASE = 'altgard-real-map-2026-10-11'


def read(path):
    return yaml.safe_load((SOURCE / path).read_text(encoding='utf-8'))


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def build():
    definitions = [
        ('ore','Minérios','diamond','#92b6ce'), ('gems','Gemas','diamond','#a996ef'),
        ('herbs','Ervas','leaf','#74d4a5'), ('wood','Madeira','wood','#c9ad7d'),
        ('aquatic','Vida aquática','circle','#69bfde'), ('fruit','Frutas','circle','#e7ac77'),
        ('vegetable','Vegetais','leaf','#aec777'), ('aether','Odyle','star','#c394eb'),
        ('traces','Vestígios','star','#75cfb8'), ('cubes','Hidden Cubes','cube','#e6c576')]
    categories = [dict(id=i,name=n,icon=s,color=c) for i,n,s,c in definitions]
    resources = []
    # Names and kinds checked against the cited publisher. No spawn positions inferred.
    names = {'aquatic':['Conide','Cypri','Inina','Pujery'], 'fruit':['Mela','Raydam'],
             'gems':['Diamond','Ruby','Sapphire'], 'herbs':['Aria','Azpha','Calendula','Targena'],
             'wood':['Asvata','Yggdrasil'], 'ore':['Orichalcum'],
             'vegetable':['Coriolus','Kukuru','Morfa','Ohkra'], 'aether':['Odyle']}
    for category, values in names.items():
        for name in values:
            resources.append(dict(id=name.lower(),name=name,category=category,subcategory=category,
                rarity='unknown',source='https://aion2maps.com/gathering/',
                verification='Nome e categoria conferidos na fonte em 11/10/2026',
                notes='Catálogo publicado inclui regiões Global e TW. Coordenadas de coleta não incorporadas; raridade não informada.'))
    for key,name in [('traces','Vestígios de Daeva • KR/TW'),('cubes','Hidden Cube • KR/TW')]:
        resources.append(dict(id=key,name=name,category=key,subcategory=key,rarity='unknown',
            source=URL,verification='Registro comunitário; LATAM não confirmado',
            notes='Origem asiática, anterior ao Global. Não representa cobertura Global.'))
    dataset = dict(schema_version=1,demo=False,title='Strigoi • catálogo publicado e atlas comunitário',
        release=RELEASE, checked_on=CHECKED,
        coverage='LATAM / Agenda e catálogo com fontes • Atlas de referência KR/TW, sem confirmação Global',
        regions=[dict(id='elyos',name='Elyos'),dict(id='asmodian',name='Asmodians')],
        maps=[],categories=categories,subcategories=[dict(id=i,category=i,name=n) for i,n,_,_ in definitions],
        resources=resources,points=[],cubes=[])
    transformations={}
    for upstream,map_id,name,faction in [('World_L_A','verteron','Verteron','elyos'),('World_D_A','altgard','Altgard','asmodian')]:
        markers=read(f'markers/{upstream}.yaml')['markers']
        polygons=read(f'regions/{upstream}.yaml')['regions']
        selected=[p for p in markers if p['subtype'] in ('hiddenCube','monolithMaterial')]
        coords=[(p['x'],p['y']) for p in selected]+[tuple(p) for r in polygons for poly in r['borders'] for p in poly]
        xmin=0; xmax=8192
        ymin=0; ymax=8192
        def project(x,y):
            # Upstream CRS.Simple: x east, y north. Qt origin is top-left.
            return ((x-xmin)/(xmax-xmin),(ymax-y)/(ymax-ymin))
        width=1200; height=round(width*(ymax-ymin)/(xmax-xmin))
        transformations[map_id]=dict(upstream=upstream,xmin=xmin,xmax=xmax,ymin=ymin,ymax=ymax,
            conversion='x=(source_x-xmin)/(xmax-xmin); y=(ymax-source_y)/(ymax-ymin)',
            counts=dict(Counter(p['subtype'] for p in selected)))
        svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             f'<rect width="{width}" height="{height}" fill="#101b2b"/>']
        for x in range(0,width,100):
            svg.append(f'<path d="M{x},0 V{height}" stroke="#1b293c"/>')
        for y in range(0,height,100):
            svg.append(f'<path d="M0,{y} H{width}" stroke="#1b293c"/>')
        for index,region in enumerate(polygons):
            for poly in region['borders']:
                points=' '.join(f'{x*width:.3f},{y*height:.3f}' for x,y in (project(*p) for p in poly))
                svg.append(f'<polygon points="{points}" fill="{["#243c4d","#263449","#243b40"][index%3]}" stroke="#567386" stroke-width="1.5"/>')
        svg.extend([f'<text x="30" y="40" fill="#e0daee" font-family="Segoe UI" font-size="23">{escape(name)} · KR/TW</text>',
                    '<text x="30" y="66" fill="#9bb0bf" font-family="Segoe UI" font-size="13">Diagrama de regiões • geometria comunitária • N ↑</text>', '</svg>'])
        image=f'maps/{map_id}-community.svg'
        (ROOT/'app/assets'/image).write_text('\n'.join(svg),encoding='utf-8')
        image=f'maps/{map_id}-world.webp'
        assert (ROOT/'app/assets'/image).is_file(), image
        dataset['maps'].append(dict(id=map_id,name=f'{name} • referência KR/TW',region=faction,image=image,
            width=8192,height=8192,supports_overlay=False,
            source='Mapa real: NCSOFT / Aion2 Interactive Map, distribuído por problem-xyz. Posições comunitárias KR/TW; LATAM não confirmado.'))
        for p in selected:
            cube=p['subtype']=='hiddenCube'; x,y=project(p['x'],p['y'])
            resource='cubes' if cube else 'traces'
            point=dict(id=p['id'],name=f'{"Hidden Cube" if cube else "Vestígio"} {p.get("name","")} · {name}'.replace('  ',' '),
                map_id=map_id,resource_id=resource,x=x,y=y,source=URL+f'/blob/{COMMIT}/public/data/markers/{upstream}.yaml',
                certainty='possible',visible_in_overlay=False,
                notes='Posição da base comunitária KR/TW. Existência e posição LATAM não confirmadas. '+
                    (f'Distrito na fonte: {p["region"]}.' if p.get('region') else ''))
            if cube:
                point['route_hint']='Rota e condição subaquática não verificadas.'
            dataset['cubes' if cube else 'points'].append(point)
    dataset['maps'].sort(key=lambda m: m['id'] != 'altgard')
    write(ROOT/'app/data/dataset.json',dataset)
    manifest=dict(checked_on=CHECKED,release=RELEASE,source_url=URL,commit=COMMIT,
        author='Yihao Liu (tc-imba) e colaboradores',license='CC BY-NC 4.0',
        license_url='https://creativecommons.org/licenses/by-nc/4.0/',
        changes='Seleção de dois mapas e duas classes de pontos; normalização com inversão de Y, mapa integral de 8192 pixels, imagens WebP originais e nomes traduzidos.',
        global_validation=False,transformations=transformations,coordinate_corrections="coordinate-corrections.json",
        files={str(p.relative_to(SOURCE)).replace('\\','/'):sha256(p.read_bytes()).hexdigest() for p in sorted(SOURCE.rglob('*')) if p.is_file()})
    write(ROOT/'app/data/community-provenance.json',manifest)
    print(f'{len(dataset["points"])} vestígios + {len(dataset["cubes"])} cubos; 21 recursos catalogados sem posições de coleta.')


if __name__=='__main__':
    build()
