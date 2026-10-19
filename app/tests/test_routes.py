# SPDX-License-Identifier: GPL-3.0-only
"""Route ordering, persistence and fail-closed progression without a live game."""
import json
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from app.core.models import RouteSettings
from app.modules.routes.models import FarmRoute,RouteLibrary,Stop,Vertex
from app.modules.routes.planner import generate,rebuild,validate_references,reviewed_path
from app.modules.routes.service import RouteService
from app.services.context import AppContext


def route(mode='open'):
    stops=[Stop(id=str(i),name=f'Stop {i}',x=x,y=.5,custom=True) for i,x in enumerate([.1,.2,.3])]
    return FarmRoute.model_validate(rebuild(FarmRoute.model_construct(id='test',name='My route',map_id='altgard',resources=[],mode=mode,stops=stops,legs=[])).model_dump())


@pytest.fixture
def service(qapp,tmp_path):
    result=RouteService(AppContext(tmp_path));result.timer.stop()
    yield result
    result.shutdown()


def test_real_azpha_generation_is_bounded_and_uses_exact_atlas_ids(service):
    data=service.dataset
    rows=[p for p in data.all_points if p.map_id=='altgard' and p.resource_id=='azpha']
    assert len(rows)==150
    result=generate(data,'altgard',['azpha'],12,'loop')
    known={p.id:p for p in rows}
    assert len(result.stops)==len(result.legs)==12
    assert len({p.id for p in result.stops})==12
    for p in result.stops:assert (p.x,p.y)==(known[p.id].x,known[p.id].y)
    assert all(not l.reviewed and l.origin=='suggested' for l in result.legs)
    assert result==FarmRoute.model_validate(result.model_dump())
    one=generate(data,'altgard',['azpha'],3,'open',Vertex(x=rows[80].x,y=rows[80].y))
    assert one.stops[0].id==rows[80].id and len(one.legs)==2
    for bad in [1,61]:
        with pytest.raises(ValueError):generate(data,'altgard',['azpha'],bad)
    with pytest.raises(ValueError):generate(data,'altgard',['not-a-resource'])
    other=next(p.resource_id for p in data.all_points if p.map_id=='altgard' and p.resource_id!='azpha' and p.enabled)
    mixed=generate(data,'altgard',['azpha',other],8)
    assert {p.resource_id for p in mixed.stops}=={'azpha',other}


def test_library_keeps_custom_geometry_and_never_resumes_on_restart(service,tmp_path):
    service.draft=route();service.save();service.start()
    other=RouteService(AppContext(tmp_path));other.timer.stop()
    try:
        assert not other.active and len(other.library.routes)==1
        other.load('test');assert other.draft==route()
        exported=tmp_path/'shared.json';other.export_file(exported)
        other.import_file(exported)
        assert len(other.library.routes)==2 and other.library.routes[1].id!='test'
        other.delete('test');assert len(other.library.routes)==1
    finally:other.shutdown()


def test_import_drops_external_review_and_invalid_import_is_atomic(service,tmp_path):
    r=route();r.legs[0].origin='edited';r.legs[0].reviewed=True
    path=tmp_path/'shared.json';path.write_text(RouteLibrary(routes=[r]).model_dump_json())
    service.import_file(path);assert not service.library.routes[0].legs[0].reviewed
    previous=service.path.read_bytes()
    invalid=r.model_dump();invalid['stops'][0]['x']=float('nan')
    path.write_text(json.dumps(dict(schema_version=1,routes=[invalid])))
    with pytest.raises(ValueError):service.import_file(path)
    assert service.path.read_bytes()==previous


def test_changed_atlas_reference_cannot_start(service):
    r=service.plan('altgard',['azpha'],4)
    r.stops[0].x+=.01
    with pytest.raises(ValueError):service.start(r)
    assert not service.active


def test_reviewed_paths_are_directed_and_never_join_nearby_floors():
    r=route();r.legs[0].origin='edited';r.legs[0].reviewed=True
    r.legs[1].origin='recorded';r.legs[1].reviewed=True
    a,b,c=r.stops
    assert reviewed_path(a,c,'altgard',[r])==r.legs[0].vertices+r.legs[1].vertices[1:]
    assert reviewed_path(c,a,'altgard',[r]) is None
    assert reviewed_path(a,c,'other-map',[r]) is None
    moved=a.model_copy(update={'y':a.y+.00001})
    assert reviewed_path(moved,c,'altgard',[r]) is None
    r.legs[1].origin='suggested'
    assert reviewed_path(a,c,'altgard',[r]) is None


def observe(service,x,t=100,**kwargs):
    args=dict(map_id='altgard',game=(10,20),observed_at=t,now=t,radius=.002)
    args.update(kwargs)
    service.observe(Vertex(x=x,y=.5),**args)


def setup(service,mode='open'):
    service.start(route(mode));service.set_context(True,(10,20))


def test_visit_requires_fresh_continuous_dwell_and_does_not_touch_inventory(service):
    setup(service);before=service.context.prefs.model_dump()
    observe(service,.1);assert service.current==0
    observe(service,.1,101.21);assert service.current==1
    assert service.visited==['0'] and service.context.prefs.model_dump()==before
    # Remaining at the previous stop cannot consume another target.
    observe(service,.1,103);observe(service,.1,105);assert service.current==1
    observe(service,.2,106);observe(service,.2,107.21);assert service.current==2
    observe(service,.3,108);observe(service,.3,109.21)
    assert service.complete and service.target is None


@pytest.mark.parametrize('override',[dict(map_id='other'),dict(game=(10,21)),dict(observed_at=99),dict(observed_at=101)])
def test_bad_readings_cannot_advance(service,override):
    setup(service);observe(service,.1)
    observe(service,.1,100,**override)
    assert service.position is None and service.inside_since is None and service.current==0


def test_focus_menu_pause_and_teleport_never_advance(service):
    setup(service);observe(service,.1)
    service.set_context(False,(10,20));observe(service,.1,102)
    assert service.current==0 and service.position is None
    service.set_context(True,(10,20));observe(service,.1,103);service.pause();observe(service,.1,105)
    assert service.current==0
    service.pause();observe(service,.1,106);observe(service,.2,106.1)
    assert service.position is None and service.current==0
    service.set_context(True,(11,20));assert service.paused and service.suspended


def test_loop_visits_return_stop_and_explicit_skip_remains_separate(service):
    setup(service,'loop')
    for _ in range(3):service.skip()
    assert not service.complete and service.target.id=='0' and service.current==3
    service.skip();assert service.complete and service.skipped==['0','1','2','0'] and not service.visited


def test_recording_never_bridges_a_lost_reading(service):
    setup(service);service.set_recording(True)
    observe(service,.1);observe(service,.1,101.21)
    observe(service,.15,102);service.lose_position()
    observe(service,.18,103);observe(service,.2,104);observe(service,.2,105.21)
    assert service.current==2 and not service.recordings
    observe(service,.25,106);observe(service,.3,107);observe(service,.3,108.21)
    assert set(service.recordings)=={1}
    service.use_recorded();assert service.draft.legs[0].origin=='suggested'
    assert service.draft.legs[1].origin=='recorded' and not service.draft.legs[1].reviewed
    assert FarmRoute.model_validate(service.draft.model_dump())


def test_edits_preserve_order_and_custom_points_stay_with_their_map(service):
    service.draft=route();service.edit_passage(0,Vertex(x=.18,y=.51));service.edit_passage(0,Vertex(x=.12,y=.51))
    assert [p.x for p in service.draft.legs[0].vertices]==[.1,.12,.18,.2]
    service.reverse();assert [p.id for p in service.draft.stops]==['2','1','0']
    assert FarmRoute.model_validate(service.draft.model_dump())
    service.draft=None;service.custom_pair('altgard',Vertex(x=.4,y=.4))
    service.custom_pair('verteron',Vertex(x=.5,y=.5));assert service.draft is None
    service.custom_pair('verteron',Vertex(x=.6,y=.5));assert service.draft.map_id=='verteron'
    assert [p.x for p in service.draft.stops]==[.5,.6]


def test_zone_and_identity_changes_pause_but_invalid_identity_is_ignored(service):
    setup(service)
    event=lambda **p:dict(type='event',kind='SelfIdentifiedEvent',payload=p)
    service.from_feed(event(ServerId=1,Name='Player'));assert service.identity==(1,'Player')
    service.from_feed(event(ServerId=None,Name=''));assert not service.paused
    service.from_feed(event(ServerId=1,Name='Alt'));assert service.paused and service.suspended


@pytest.mark.parametrize('profile',[dict(anchor=(-.1,.5)),dict(anchor=(.5,float('nan'))),dict(arrow_shape=[(float('inf'),0)]),dict(arrow_area=float('nan'))])
def test_invalid_arrow_profiles_are_rejected(profile):
    with pytest.raises(ValidationError):RouteSettings(**profile)


def test_fixed_minimap_center_advances_from_stop_one_to_two_without_arrow_setup(service):
    import numpy as np
    from app.modules.overlay.selection import CaptureArea
    from app.modules.overlay.tracking import Registration
    from app.modules.routes.position import locate
    setup(service)
    assert service.context.prefs.routes.anchor is None
    a=CaptureArea(map_id='altgard',screen_name='test',screen_x=0,screen_y=0,screen_width=2560,
        screen_height=1440,pixel_ratio=1.5,x=2000,y=60,width=330,height=220,view_kind='minimap')
    reg=Registration(np.array([[1500,0,97.5],[0,1500,-585]],float),25,.95)
    point,radius=locate((330,495,3),reg,a)
    assert point==Vertex(x=.1,y=.5)
    for t in [100,100.2,100.41]:
        service.observe(point,map_id='altgard',game=(10,20),observed_at=t,now=t,radius=radius)
    assert service.current==1 and service.target.id=='1' and service.visited==['0']
    # A stationary player cannot consume stop two after completing stop one.
    for t in [100.6,100.8,101.01]:
        service.observe(point,map_id='altgard',game=(10,20),observed_at=t,now=t,radius=radius)
    assert service.current==1
