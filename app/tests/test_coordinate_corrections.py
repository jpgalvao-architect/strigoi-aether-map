# SPDX-License-Identifier: GPL-3.0-only
import json
from hashlib import sha256
import cv2
import numpy as np
import pytest
from app.core.corrections import upgrade_cube_sites
from app.core.models import Dataset, EventFeed, Gatherable, HiddenCube, Preferences
from app.infrastructure.storage import PACKAGE, atomic_json, load_model
from app.services.context import AppContext
from app.modules.gatherables.service import FilterQuery, filter_points


def manifest(name):
    return json.loads((PACKAGE/f'data/{name}.json').read_text(encoding='utf-8'))


def previous_dataset(replacement=True):
    data=load_model(PACKAGE/'data/dataset.json',Dataset)
    data.cubes=[c for c in data.cubes if c.resource_id=='cubes']
    data.resources=[r for r in data.resources if r.id!='cube-spawns']
    old_resource=Gatherable.model_validate(manifest('cube-sites-provenance')['legacy_resource'])
    data.resources=[old_resource if r.id=='cubes' else r for r in data.resources]
    data.release='sa-live-overlay-v030'
    if replacement:
        record=manifest('coordinate-corrections')['corrections'][0]
        data.cubes=[HiddenCube.model_validate(record['replacement']) if c.id==record['original']['id'] else c for c in data.cubes]
    return data


def upgrade(data):
    return upgrade_cube_sites(data,load_model(PACKAGE/'data/dataset.json',Dataset),manifest('cube-sites-provenance'),manifest('coordinate-corrections'))


def test_rolls_back_only_exact_replacement_and_adds_distinct_sites():
    old=previous_dataset()
    new,changes=upgrade(old)
    record=manifest('coordinate-corrections')['corrections'][0]
    target=next(c for c in new.cubes if c.id==record['original']['id'])
    assert target.model_dump(mode='json')==record['original']
    assert len(new.cubes)==3037 and new.points==old.points and new.maps==old.maps
    assert sum(a!=b for a,b in zip(old.cubes,new.cubes[:226]))==1
    assert old==previous_dataset()
    assert upgrade(new)==(new,[])


@pytest.mark.parametrize('replacement',[False,True])
def test_migration_preserves_annotations_visits_and_agenda(qapp,tmp_path,replacement):
    old=previous_dataset(replacement)
    old.points[0].notes='Minha anotação'
    cube_id=old.cubes[0].id
    atomic_json(tmp_path/'dataset.json',old)
    atomic_json(tmp_path/'preferences.json',Preferences(content_release='sa-live-overlay-v030',visited={cube_id},disabled_categories={'ore'},disabled_resources={'iron'},agenda_profile='curated-sa'))
    feed=load_model(PACKAGE/'data/profiles/curated-sa.json',EventFeed)
    atomic_json(tmp_path/'events-cache.json',feed)
    context=AppContext(tmp_path)
    assert load_model(tmp_path/'dataset.v042-backup.json',Dataset)==old
    assert context.dataset.points==old.points and len(context.dataset.cubes)==3037
    assert context.prefs.visited=={cube_id}
    assert context.prefs.disabled_resources=={'iron','cubes'}
    assert context.prefs.disabled_categories=={'ore'}
    assert context.feed==feed and context.prefs.agenda_profile=='curated-sa'
    assert len(filter_points(context.dataset,context.prefs,FilterQuery(cubes_only=True)))==2811
    # Explicitly re-enabling historical records survives restart.
    context.prefs.disabled_resources.discard('cubes')
    context.save()
    restarted=AppContext(tmp_path)
    assert restarted.dataset==context.dataset
    assert 'cubes' not in restarted.prefs.disabled_resources and not restarted.messages
    assert load_model(tmp_path/'dataset.v042-backup.json',Dataset)==old


@pytest.mark.parametrize('edited',['coordinates','notes','map'])
def test_custom_target_is_preserved(edited):
    old=previous_dataset();record=manifest('coordinate-corrections')['corrections'][0]
    target=next(c for c in old.cubes if c.id==record['original']['id'])
    if edited=='coordinates':target.x+=.001
    elif edited=='notes':target.notes='Minha coordenada anotada manualmente'
    else:old.maps[0].name='Meu mapa personalizado'
    new,_=upgrade(old)
    assert next(c for c in new.cubes if c.id==target.id)==target
    if edited=='map':
        assert not any(c.resource_id=='cube-spawns' and c.map_id=='altgard' for c in new.cubes)
        assert sum(c.resource_id=='cube-spawns' for c in new.cubes)==1440
    else:assert len(new.cubes)==3037


def test_custom_resource_and_existing_site_are_not_overwritten():
    data=load_model(PACKAGE/'data/dataset.json',Dataset)
    data.cubes[-1].notes='Minha posição'
    assert upgrade(data)==(data,[])
    old=previous_dataset()
    resource=next(r for r in data.resources if r.id=='cube-spawns').model_copy(deep=True)
    resource.source='Minha fonte'
    old.resources.append(resource)
    new,_=upgrade(old)
    assert not any(c.resource_id=='cube-spawns' for c in new.cubes)
    assert next(r for r in new.resources if r.id=='cube-spawns')==resource


def test_fresh_default_has_no_legacy_duplicates(qapp,tmp_path):
    context=AppContext(tmp_path)
    cubes=filter_points(context.dataset,context.prefs,FilterQuery(cubes_only=True))
    assert len(cubes)==2811 and all(c.resource_id=='cube-spawns' for c in cubes)
    assert len(filter_points(context.dataset,context.prefs,FilterQuery()))==9356
    assert not context.prefs.overlay.enabled


def test_all_sites_exactly_match_licensed_snapshots():
    data=load_model(PACKAGE/'data/dataset.json',Dataset)
    provenance=manifest('cube-sites-provenance')
    assert provenance['counts']=={'altgard':1371,'verteron':1440}
    assert not provenance['sa_individually_validated'] and not provenance['sa_exclusive']
    sites={c.id:c for c in data.cubes if c.resource_id=='cube-spawns'}
    for map_id,count in provenance['counts'].items():
        path=PACKAGE.parent/f'data-sources/object-sets/{map_id}.json'
        assert sha256(path.read_bytes()).hexdigest()==provenance['files'][path.name]
        nodes=[n for n in json.loads(path.read_text(encoding='utf-8'))['nodes'] if n['categoryId']=='hidden-cube-'+map_id]
        assert len(nodes)==count
        assert len({(n['x'],n['y']) for n in nodes})==count
        for node in nodes:
            point=sites[f'spawn-{map_id}-{node["id"]}']
            assert (point.x,point.y)==(node['x']/100,node['y']/100)
            assert point.underwater is None and point.certainty=='possible'
            assert node['id'].removeprefix('cube-').rsplit('-',1)[0] in point.notes


def test_basfelt_has_separate_candidates_without_player_anchor_override():
    from app.modules.overlay.tracking import MapRegistration
    frame=cv2.imdecode(np.fromfile(PACKAGE/'tests/fixtures/user-minimap-basfelt.png',dtype=np.uint8),cv2.IMREAD_COLOR)
    registration=MapRegistration(PACKAGE/'assets/maps/altgard-world.webp',minimap=True).find(frame,minimum=18)
    assert registration is not None
    cubes={c.id:c for c in load_model(PACKAGE/'data/dataset.json',Dataset).cubes}
    record=manifest('coordinate-corrections')['corrections'][0]
    old=cubes[record['original']['id']]
    nearby=cubes['spawn-altgard-cube-BasfeltRuins_01_B2-01']
    neighbor=cubes['spawn-altgard-cube-BasfeltRuins_01_B2-02']
    anchor=np.array(record['evidence']['player_anchor'])
    distance=lambda c:np.linalg.norm(np.array(registration.project(c.x,c.y))-anchor)
    assert old.model_dump(mode='json')==record['original']
    assert distance(old)>30 and distance(nearby)<10 and distance(neighbor)>30
    assert np.linalg.norm(np.array(registration.project(nearby.x,nearby.y))-registration.project(neighbor.x,neighbor.y))>30
    # Proximity supports this candidate, not exact center or regional validation.
    assert nearby.certainty=='possible'
