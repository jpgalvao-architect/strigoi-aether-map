# SPDX-License-Identifier: GPL-3.0-only
"""Reconcile announced summons using observed links, never a guessed player."""
from collections import defaultdict


def inferred_owners(encounter):
    players = {key: entity for key, entity in encounter.entities.items() if entity.kind == "player"}
    scalars, skills, targets = defaultdict(set), defaultdict(set), defaultdict(set)
    for hit in encounter.hits:
        skills[hit.source].add(hit.skill)
        targets[hit.source].add(hit.target)
        if hit.power_scalar > 10_000:
            scalars[hit.source].add(hit.power_scalar)
    links = {}
    variants_by_summon, casts_by_variant = defaultdict(list), defaultdict(list)
    for cast in encounter.casts:
        if cast.actor in players:
            casts_by_variant[cast.skill // 10].append(cast)
        elif cast.actor == cast.target:
            variants_by_summon[cast.actor].append(cast)
    for key, entity in encounter.entities.items():
        if entity.kind != "summon" or entity.owner or entity.owner_name:
            continue  # Explicit identity/name always takes precedence.
        variants = {cast.skill // 10 for cast in variants_by_summon[key] if cast.time >= entity.spawn_time}
        casters = {cast.actor for variant in variants for cast in casts_by_variant[variant]
                   if entity.spawn_time - 3000 <= cast.time <= entity.spawn_time + 300}
        if len(casters) == 1:
            links[key] = (next(iter(casters)), "cast")
            continue
        if casters or encounter.pvp or not scalars[key]:
            continue  # Ambiguous cast evidence and PvP never use scalar fallback.
        end = encounter.end if encounter.end is not None else encounter.observed_until
        if end - entity.spawn_time < 3000:
            continue  # Allow the direct owner announcement to arrive first.
        matches = {actor for actor in players if scalars[key] & scalars[actor]}
        if len(matches) == 1:
            owner = next(iter(matches))
            if (players[owner].job == 6 and len(skills[owner]) >= 3
                    and scalars[key] <= scalars[owner] and targets[key] & targets[owner]):
                links[key] = (owner, "scalar")
    return links
