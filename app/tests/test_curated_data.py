# SPDX-License-Identifier: GPL-3.0-only
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import re

import pytest

from app.core.models import Dataset, EventFeed
from app.infrastructure.storage import PACKAGE, atomic_json, load_model, resolve_map_image
from app.modules.events.service import display_time, occurrences
from app.services.context import AppContext


def test_inspiration_reference_preserved_in_source_only():
    assert sha256((PACKAGE.parent/'data-sources/branding/strigoi-inspiration.png').read_bytes()).hexdigest() == 'e5c77eb46569e1060d731a19835d264bfdcb5373962b2b6c0470134e7d3f8c2e'


def test_source_checksums_and_all_coordinates():
    dataset=load_model(PACKAGE/'data/dataset.json',Dataset)
    manifest=json.loads((PACKAGE/'data/community-provenance.json').read_text(encoding='utf-8'))
    overrides=json.loads((PACKAGE/'data/coordinate-corrections.json').read_text(encoding='utf-8'))
    assert overrides['status']=='withdrawn'
    source=PACKAGE.parent/'data-sources/community'
    for file,digest in manifest['files'].items():
        assert sha256((source/file).read_bytes()).hexdigest()==digest
    assert not dataset.demo
    assert len(dataset.points)==6545 and len(dataset.cubes)==3037
    assert len([r for r in dataset.resources if r.id not in ('cubes','cube-spawns','traces')])==21
    assert all(p.certainty=='possible' and p.visible_in_overlay for p in dataset.all_points)
    assert all(r.rarity=='unknown' for r in dataset.resources)
    for definition in dataset.maps:
        assert resolve_map_image(definition.image).is_file()
        assert definition.supports_overlay
        t=manifest['transformations'][definition.id]
        original=(source/f'markers/{t["upstream"]}.yaml').read_text(encoding='utf-8')
        records={}
        for block in re.split(r'(?m)^- category: ',original)[1:]:
            def field(name):
                return re.search(rf'(?m)^  {name}: (.+)$',block).group(1)
            records[field('id')]=(float(field('x')),float(field('y')))
        for point in [p for p in dataset.all_points if p.map_id==definition.id and not p.id.startswith(('gather-','spawn-'))]:
            x,y=records[point.id]
            expected=((x-t['xmin'])/(t['xmax']-t['xmin']),(t['ymax']-y)/(t['ymax']-t['ymin']))
            assert (point.x,point.y)==pytest.approx(expected)


def test_latam_source_clock_and_utc_resets():
    feed=load_model(PACKAGE/'data/profiles/curated-sa.json',EventFeed)
    assert not feed.demo and len(feed.events)==9
    events={e.id:e for e in feed.events}
    now=datetime(2026,10,12,0,tzinfo=UTC)
    siege=occurrences([events['latam-siege']],now)[0]
    assert siege.starts_at==datetime(2026,10,13,0,tzinfo=UTC)
    assert '21:00' in display_time(siege.starts_at,'America/Sao_Paulo')
    reset=occurrences([events['global-weekly-reset']],now)[0]
    assert reset.starts_at==datetime(2026,10,14,7,tzinfo=UTC)
    assert '04:00' in display_time(reset.starts_at,'America/Sao_Paulo')
    assert all(e.verified_on and e.source.startswith('https://') for e in feed.events)


def test_exact_demo_migrates_with_backup(qapp,tmp_path,dataset,feed):
    atomic_json(tmp_path/'dataset.json',dataset)
    atomic_json(tmp_path/'events-cache.json',feed)
    context=AppContext(tmp_path)
    assert not context.dataset.demo and not context.feed.demo
    assert context.prefs.timezone=='America/Sao_Paulo'
    assert load_model(tmp_path/'dataset.v010-backup.json',Dataset)==dataset
    assert load_model(tmp_path/'events-cache.v010-backup.json',EventFeed)==feed


def test_custom_import_preserved_on_upgrade(qapp,tmp_path,dataset,feed):
    dataset.points[0].notes='Minha anotação personalizada'
    feed.events[0].name='Minha agenda personalizada'
    atomic_json(tmp_path/'dataset.json',dataset)
    atomic_json(tmp_path/'events-cache.json',feed)
    context=AppContext(tmp_path)
    assert context.dataset==dataset and context.feed==feed
    assert not list(tmp_path.glob('*.v010-backup.json'))


def test_dynamic_overlay_requires_explicit_screen_selection(qapp,tmp_path):
    from app.modules.overlay.service import OverlayService
    context=AppContext(tmp_path)
    service=OverlayService(context)
    with pytest.raises(ValueError,match='Selecionar área'):
        service.start()
    assert service.worker is None
    service.watchdog.stop()
    service.stop()


def test_agenda_displays_each_schedule_and_switches_source(qapp,tmp_path):
    from app.ui.events_page import EventsPage
    page=EventsPage(AppContext(tmp_path))
    assert len(page.items)==10
    assert len({i.event.id for i in page.items})==10
    page.profile.setCurrentIndex(page.profile.findData('curated-sa'))
    assert len(page.items)==9
    page.unique.setChecked(False)
    assert len(page.items)==24
    page.timer.stop()
    page.close()


def test_real_map_files_match_pinned_source(qapp):
    from PySide6.QtGui import QImageReader
    manifest=json.loads((PACKAGE/'data/map-art-provenance.json').read_text(encoding='utf-8'))
    for record in manifest['maps']:
        path=PACKAGE/'assets'/record['image']
        assert sha256(path.read_bytes()).hexdigest()==record['sha256']
        reader=QImageReader(str(path))
        assert reader.canRead()
        assert reader.size().width()==8192 and reader.size().height()==8192


def test_altgard_default_picklists_and_saved_choice(qapp,tmp_path):
    from app.ui.main_window import MainWindow
    context=AppContext(tmp_path)
    window=MainWindow(context)
    for combo in [window.atlas.maps,window.cubes.maps,window.catalog.map_combo,window.overlay_page.maps]:
        assert combo.currentData()=='altgard'
    assert window.atlas.view.map.image=='maps/altgard-world.webp'
    assert window.atlas.view._markers
    # Changing a default is retained on future launches, rather than being forced every time.
    window.atlas.maps.setCurrentIndex(window.atlas.maps.findData('verteron'))
    window.catalog.map_combo.setCurrentIndex(window.catalog.map_combo.findData('verteron'))
    window.close()
    reloaded=AppContext(tmp_path)
    assert reloaded.prefs.map_id=='verteron'
    assert reloaded.prefs.catalog_map_id=='verteron'


def test_v020_upgrade_preserves_visits_and_backs_up_coordinates(qapp,tmp_path):
    from app.core.models import Preferences
    old=load_model(PACKAGE/'tests/fixtures/v020-dataset.json',Dataset)
    visited=old.cubes[0].id
    atomic_json(tmp_path/'dataset.json',old)
    atomic_json(tmp_path/'preferences.json',Preferences(map_id='verteron',visited={visited}))
    context=AppContext(tmp_path)
    assert context.prefs.map_id=='altgard'
    assert visited in context.prefs.visited
    assert all(m.image.endswith('-world.webp') for m in context.dataset.maps)
    assert load_model(tmp_path/'dataset.v020-backup.json',Dataset)==old
