# SPDX-License-Identifier: GPL-3.0-only
"""Reference farming sites are an ephemeral atlas layer, never user dataset edits."""
from collections import defaultdict

from app.core.models import Category, Gatherable, PointOfInterest, Subcategory
from app.infrastructure.storage import PACKAGE, load_model
from app.modules.pets.models import PetSites


class PetFarm:
    def __init__(self, catalogue):
        self.sites = load_model(PACKAGE/'data/pet-sites.json', PetSites)
        self.by_npc = defaultdict(list)
        for site in self.sites.sites:
            self.by_npc[site.npc_code].append(site)
        self.by_pet = {pet.id: [site for source in pet.monsters for site in self.by_npc[source.npc_code]]
                       for pet in catalogue.pets}
        self._base = None
        self._view = None

    def dataset(self, base, catalogue):
        if self._base is base:
            return self._view
        # Only join to the original full-image map frames. Imported maps need their own evidence.
        supported = {m.id for m in base.maps if m.image == f'maps/{m.id}-world.webp'
                     and m.width == 8192 and m.height == 8192}
        categories, subs, resources, points = [], [], [], []
        if 'pets' in {c.id for c in base.categories} or 'pet-farm' in {s.id for s in base.subcategories}:
            self._base, self._view = base, base
            return base  # Do not collide with a user-defined category.
        categories.append(Category(id='pets', name='Pets', icon='pets', color='#bca5e9'))
        subs.append(Subcategory(id='pet-farm', category='pets', name='Almas de pets'))
        existing_resources = {r.id for r in base.resources}
        existing_points = {p.id for p in base.points}
        for pet in catalogue.pets:
            sites = [s for s in self.by_pet[pet.id] if s.map_id in supported]
            if not sites:
                continue
            key = f'pet-{pet.id}'
            if key in existing_resources:
                continue
            resources.append(Gatherable(id=key, name=pet.name, category='pets', subcategory='pet-farm',
                source=pet.source, verification='Referência do cliente Global; presença regional não confirmada.'))
            names = {m.npc_code:m.name for m in pet.monsters}
            for site in sites:
                if f'{key}-{site.id}' in existing_points:
                    continue
                points.append(PointOfInterest(id=f'{key}-{site.id}', name=names[site.npc_code],
                    map_id=site.map_id, resource_id=key, x=site.x, y=site.y,
                    source=site.source, certainty='possible',
                    notes=f'{pet.name} · Local de referência do monstro; presença atual e compatibilidade SA não confirmadas.'))
        view = base.model_copy(update={'categories':[*base.categories,*categories],
            'subcategories':[*base.subcategories,*subs], 'resources':[*base.resources,*resources],
            'points':[*base.points,*points]})
        self._base, self._view = base, view
        return view
