# SPDX-License-Identifier: GPL-3.0-only
"""Atomic collection edits preserve unknown, observed and manual states."""
from datetime import UTC, datetime
import shutil
from uuid import uuid4

from app.infrastructure.storage import PACKAGE, atomic_json, load_model, recover_model
from app.modules.pets.models import PetCatalogue, PetCollection, PetEntry, PetProfile, PetProgress


class PetStore:
    def __init__(self, directory):
        self.path = directory/'pets-collection.json'
        self.catalogue = load_model(PACKAGE/'data/pets.json', PetCatalogue)
        self.by_id = {pet.id: pet for pet in self.catalogue.pets}
        self.collection, self.warning = recover_model(self.path, PetCollection, PetCollection())

    @property
    def profile(self):
        return self.collection.profiles[self.collection.active_profile]

    def entry(self, pet_id):
        self._valid_pet(pet_id)
        return self.profile.entries.get(str(pet_id), PetEntry())

    def _valid_pet(self, pet_id):
        if type(pet_id) is not int or pet_id not in self.by_id:
            raise ValueError('Unknown pet identity')

    def commit(self, candidate):
        atomic_json(self.path, candidate)
        self.collection = candidate

    def edit(self, pet_id, **changes):
        self._valid_pet(pet_id)
        candidate = self.collection.model_copy(deep=True)
        profile = candidate.profiles[candidate.active_profile]
        entry = profile.entries.get(str(pet_id), PetEntry())
        entry = PetEntry.model_validate({**entry.model_dump(), **changes})
        profile.entries[str(pet_id)] = entry
        self.commit(candidate)

    def record(self, pet_id, level, souls=None):
        progress = PetProgress(level=level, souls=souls, origin='manual',
                               updated_at=datetime.now(UTC).isoformat())
        self.edit(pet_id, manual=progress, use_manual=True)

    def select_profile(self, key):
        candidate = self.collection.model_copy(deep=True)
        candidate.active_profile = key
        self.commit(PetCollection.model_validate(candidate.model_dump()))

    def observed_profile(self, region, server, character):
        import hashlib
        digest = hashlib.sha256(character.encode('utf-8')).hexdigest()[:20]
        key = f'{region}:{server}:{digest}'
        candidate = self.collection.model_copy(deep=True)
        if key not in candidate.profiles:
            profile = PetProfile(name=f'{character} · {server}', region=region, server=server, character=character)
            if candidate.active_profile == 'local':
                # Carry user intent, never merge unverified personal progress.
                profile.entries = {pet:PetEntry(favorite=entry.favorite,goal=entry.goal)
                    for pet,entry in candidate.profiles['local'].entries.items() if entry.favorite or entry.goal != 1}
            candidate.profiles[key] = profile
        candidate.active_profile = key
        self.commit(PetCollection.model_validate(candidate.model_dump()))
        return key

    def create_profile(self, name):
        candidate = self.collection.model_copy(deep=True)
        key = uuid4().hex
        candidate.profiles[key] = PetProfile(name=name.strip())
        candidate.active_profile = key
        self.commit(PetCollection.model_validate(candidate.model_dump()))
        return key

    def import_collection(self, path):
        incoming = load_model(path, PetCollection)
        # Validate all references before replacing any user state.
        for profile in incoming.profiles.values():
            for key in profile.entries:
                if not key.isdecimal():
                    raise ValueError('Invalid pet reference')
                self._valid_pet(int(key))
        if self.path.exists():
            backup = self.path.with_name(f'pets-collection.backup-{uuid4().hex}.json')
            shutil.copy2(self.path, backup)
        self.commit(incoming)

    def export_collection(self, path):
        atomic_json(path, self.collection)

    def accept_snapshot(self, profile_key, records, *, synced_at, complete=False):
        """Absolute observed quantities; partial replies never erase absent pets."""
        if profile_key not in self.collection.profiles:
            raise ValueError('Unidentified collection scope')
        incoming = {}
        for pet_id, values in records.items():
            self._valid_pet(pet_id)
            existing = self.collection.profiles[profile_key].entries.get(str(pet_id), PetEntry()).observed
            baseline = existing.model_dump() if existing else {}
            incoming[str(pet_id)] = PetProgress.model_validate({**baseline, **values,
                'origin':'observed', 'updated_at':synced_at})
        candidate = self.collection.model_copy(deep=True)
        profile = candidate.profiles[profile_key]
        for key, progress in incoming.items():
            entry = profile.entries.setdefault(key, PetEntry())
            entry.observed = progress
        if complete:
            for key, entry in profile.entries.items():
                if key not in incoming and entry.observed is not None:
                    # The reference catalogue can contain pets unavailable in this build.
                    # An absent identity invalidates old observations; it does not prove zero.
                    entry.observed = PetProgress(origin='observed',updated_at=synced_at)
        profile.synced_at = synced_at
        self.commit(candidate)

    def select(self, *, search='', family='', state='', favorites=False):
        query = search.strip().casefold()
        result = []
        for pet in self.catalogue.pets:
            entry = self.entry(pet.id)
            if family and pet.family != family:
                continue
            if state and entry.state != state:
                continue
            if favorites and not entry.favorite:
                continue
            if query and query not in (' '.join([pet.name, pet.family, *[m.name for m in pet.monsters]])).casefold():
                continue
            result.append(pet)
        return sorted(result, key=lambda pet: (not self.entry(pet.id).favorite, pet.name.casefold(), pet.id))
