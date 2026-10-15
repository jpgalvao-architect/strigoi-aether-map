# SPDX-License-Identifier: GPL-3.0-only
from hashlib import sha256
import json

import pytest
from pydantic import ValidationError
from PySide6.QtCore import Qt
from PySide6.QtGui import QImageReader

from app.core.i18n import set_language
from app.infrastructure.storage import PACKAGE, atomic_json
from app.modules.gatherables.service import FilterQuery, filter_points
from app.modules.pets.models import PetCatalogue, PetCollection, PetEntry
from app.modules.pets.store import PetStore
from app.services.context import AppContext
from app.ui.main_window import MainWindow


def test_original_nc_portraits_and_catalogue_references(qapp):
    manifest = json.loads((PACKAGE.parent/'data-sources/pet-portraits.json').read_text(encoding='utf-8'))
    store = PetStore.__new__(PetStore)
    catalogue = PetCatalogue.model_validate_json((PACKAGE/'data/pets.json').read_text(encoding='utf-8'))
    assert len(catalogue.pets) == len(manifest['portraits']) == 208
    expected = {p['id']:p for p in manifest['portraits']}
    for pet in catalogue.pets:
        path = PACKAGE/'assets'/pet.portrait
        assert sha256(path.read_bytes()).hexdigest() == expected[pet.id]['sha256']
        assert pet.portrait_source.startswith('https://assets.playnccdn.com/static-aion2-gamedata/resources/')
        assert QImageReader(str(path)).canRead()
        assert pet.region == 'global-reference'  # Never certify SA without evidence.
        assert len({m.npc_code for m in pet.monsters}) == len(pet.monsters)


def test_unknown_is_not_zero_and_goal_is_independent_of_favorite(tmp_path):
    store = PetStore(tmp_path)
    pet = next(iter(store.by_id))
    assert store.entry(pet).state == 'unknown'
    assert not store.select(state='missing')
    store.record(pet, 0, 0)
    assert store.entry(pet).state == 'missing' and store.entry(pet).progress.souls == 0
    store.edit(pet, favorite=True, goal=3)
    store.record(pet, 1, None)
    assert store.entry(pet).state == 'growing' and store.entry(pet).favorite
    assert store.select(favorites=True)[0].id == pet
    store.record(pet, 3)
    assert store.entry(pet).state == 'complete' and store.entry(pet).favorite
    reloaded = PetStore(tmp_path)
    assert reloaded.entry(pet).goal == 3 and reloaded.entry(pet).favorite


def test_absolute_snapshot_duplicates_partial_decrease_and_manual_separation(tmp_path):
    store = PetStore(tmp_path)
    a, b = list(store.by_id)[:2]
    store.accept_snapshot('local', {a:{'level':1,'souls':20},b:{'level':2,'souls':8}},synced_at='2026-10-14T12:00:00Z')
    store.accept_snapshot('local', {a:{'level':1,'souls':20}},synced_at='2026-10-14T12:00:00Z')
    assert store.entry(a).progress.souls == 20 and store.entry(b).progress.souls == 8
    store.accept_snapshot('local', {a:{'souls':2}},synced_at='2026-10-14T12:01:00Z')
    assert store.entry(a).progress.level == 1 and store.entry(a).progress.souls == 2
    store.record(a, 2, 15)
    store.accept_snapshot('local', {a:{'level':2,'souls':3}},synced_at='2026-10-14T12:02:00Z')
    assert store.entry(a).manual.souls == 15 and store.entry(a).observed.souls == 3
    store.edit(a, use_manual=False)
    assert store.entry(a).progress.souls == 3
    before = store.path.read_bytes()
    with pytest.raises(ValueError):
        store.accept_snapshot('local', {a:{'level':-1}}, synced_at='invalid')
    assert store.path.read_bytes() == before


def test_profiles_and_import_preserve_previous_progress(tmp_path):
    store = PetStore(tmp_path)
    pet = next(iter(store.by_id))
    store.record(pet, 2, 10)
    other = store.create_profile('Outro personagem')
    assert store.entry(pet).state == 'unknown'
    store.edit(pet, favorite=True)
    export = tmp_path/'export.json'
    store.export_collection(export)
    store.select_profile('local')
    assert store.entry(pet).progress.level == 2 and not store.entry(pet).favorite
    store.import_collection(export)
    assert store.collection.active_profile == other and store.entry(pet).favorite
    assert list(tmp_path.glob('pets-collection.backup-*.json'))
    before = store.path.read_bytes()
    bad = tmp_path/'invalid.json'
    value = store.collection.model_dump()
    value['profiles'][other]['entries']['999999999'] = PetEntry().model_dump()
    atomic_json(bad, value)
    with pytest.raises(ValueError):
        store.import_collection(bad)
    assert store.path.read_bytes() == before


def test_invalid_collection_is_preserved_and_noncanonical_ids_rejected(tmp_path):
    path = tmp_path/'pets-collection.json'
    path.write_text('{broken', encoding='utf-8')
    store = PetStore(tmp_path)
    assert store.warning and store.profile.entries == {}
    assert list(tmp_path.glob('pets-collection.invalid-*.json'))
    with pytest.raises(ValidationError):
        PetCollection.model_validate({'active_profile':'local', 'profiles':{
            'local':{'name':'Local','entries':{'01004':{}}}}})


def test_farm_layer_is_ephemeral_and_selection_matches_maps(qapp, tmp_path):
    window = MainWindow(AppContext(tmp_path))
    try:
        context, service = window.context, window.pets
        original = context.dataset.model_dump_json()
        view = context.atlas_dataset
        pet = next(p for p in service.store.catalogue.pets if service.farm.by_pet[p.id])
        assert 'pets' in window.atlas.checks
        assert not window.atlas.checks['pets'].isChecked()
        assert not [p for p in filter_points(view, context.prefs, FilterQuery()) if p.resource_id.startswith('pet-')]
        window.show_pet_farm(pet.id)
        points = filter_points(view,context.prefs,FilterQuery(map_id=context.prefs.map_id, overlay=True))
        farm = [p for p in points if p.resource_id.startswith('pet-')]
        assert farm and {p.resource_id for p in farm} == {f'pet-{pet.id}'}
        assert any(p.resource_id=='cube-spawns' for p in points)
        assert context.dataset.model_dump_json() == original  # No hidden dataset migration.
        assert all(p.certainty=='possible' for p in farm)
        assert all(0<=p.x<=1 and 0<=p.y<=1 for p in farm)
        context.prefs.pets.focus_id = None
        context.prefs.pets.map_filter = 'favorites'
        service.sync_map_preferences()
        assert not [p for p in filter_points(view,context.prefs,FilterQuery()) if p.resource_id.startswith('pet-')]
        service.edit(pet.id, favorite=True)
        assert {p.resource_id for p in filter_points(view,context.prefs,FilterQuery()) if p.resource_id.startswith('pet-')} == {f'pet-{pet.id}'}
    finally:
        window.close()


def test_pets_page_keyboard_filters_languages_and_stable_navigation(qapp, tmp_path):
    window = MainWindow(AppContext(tmp_path))
    try:
        page = window.pets_page
        window.navigate('pets')
        assert window.stack.currentWidget().widget() is page
        assert page.grid.count() == 208
        page.search.setText('Klaw')
        assert page.grid.count() > 0
        assert all('klaw' in (window.pets.store.by_id[page.grid.item(i).data(Qt.ItemDataRole.UserRole)].name.lower()
                   + ' '.join(m.name.lower() for m in window.pets.store.by_id[page.grid.item(i).data(Qt.ItemDataRole.UserRole)].monsters))
                   for i in range(page.grid.count()))
        set_language('en_US');page.refresh()
        assert page.favorite.text() == 'Favorite'
        assert page.search.placeholderText() == 'Search pets or monsters…'
        window.navigate('sonar')
        assert window.pages[window.stack.currentIndex()] is window.sonar_page
        window.navigate('combat')
        assert window.pages[window.stack.currentIndex()] is window.combat_page
    finally:
        set_language('pt_BR')
        window.close()
