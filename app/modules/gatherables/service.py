# SPDX-License-Identifier: GPL-3.0-only
"""Shared filter semantics for atlas, catalogue, cubes and overlay."""
from dataclasses import dataclass

from app.core.models import Dataset, PointOfInterest, Preferences
from app.core.i18n import tr


@dataclass
class FilterQuery:
    map_id: str = ""
    category: str = ""
    subcategory: str = ""
    resource_id: str = ""
    rarity: str = ""
    search: str = ""
    overlay: bool = False
    cubes_only: bool = False


def filter_points(dataset: Dataset, prefs: Preferences, query: FilterQuery) -> list[PointOfInterest]:
    resources = {r.id: r for r in dataset.resources}
    cubes = {p.id for p in dataset.cubes}
    result = []
    for point in dataset.all_points:
        resource = resources[point.resource_id]
        if not point.enabled or resource.category in prefs.disabled_categories or resource.id in prefs.disabled_resources:
            continue
        if prefs.hide_visited and point.id in prefs.visited:
            continue
        if query.map_id and point.map_id != query.map_id:
            continue
        if query.category and resource.category != query.category:
            continue
        if query.subcategory and resource.subcategory != query.subcategory:
            continue
        if query.resource_id and resource.id != query.resource_id:
            continue
        if query.rarity and resource.rarity != query.rarity:
            continue
        if query.overlay and not point.visible_in_overlay:
            continue
        if query.cubes_only and point.id not in cubes:
            continue
        haystack = f"{point.name} {resource.name} {tr(point.name)} {tr(resource.name)} {point.notes} {resource.notes}".casefold()
        if query.search.casefold() not in haystack:
            continue
        result.append(point)
    return result
