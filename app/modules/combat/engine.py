# SPDX-License-Identifier: GPL-3.0-only
"""Observed damage only. Independent of capture, Qt, and wall-clock time."""
from dataclasses import dataclass, field, replace
from uuid import uuid4


@dataclass
class Entity:
    id: int
    name: str = ""
    server: int = 0
    kind: str = "unknown"
    owner: int = 0
    owner_name: str = ""
    job: int = 0


@dataclass
class Hit:
    time: int
    source: int
    target: int
    damage: int
    skill: int


@dataclass
class Encounter:
    id: str = field(default_factory=lambda: uuid4().hex)
    start: int = 0
    end: int | None = None
    result: str = "active"
    hits: list[Hit] = field(default_factory=list)
    entities: dict[int, Entity] = field(default_factory=dict)
    roster: set[tuple[str, int]] = field(default_factory=set)
    roster_complete: bool = False
    local_id: int = 0
    boss: int | None = None
    issues: set[str] = field(default_factory=set)
    pvp: bool = False
    team_pvp: bool = False


class CombatEngine:
    MAX_HITS = 100_000
    MAX_ENTITIES = 10_000

    @staticmethod
    def normalized_class(value):
        return value if type(value) is int and 0 <= value <= 9 else 0

    def __init__(self):
        self.entities: dict[int, Entity] = {}
        self.roster: set[tuple[str, int]] = set()
        self.roster_jobs: dict[tuple[str, int], int] = {}
        self.roster_complete = False
        self.local_id = 0
        self.run_id = ""
        self.run_name = ""
        self.active = False
        self.encounters: list[Encounter] = []
        self.current: Encounter | None = None
        self.boss: int | None = None
        self.last_time = 0
        self.capture_session = ""
        self.last_sequence = 0
        self.map_id: int | None = None
        self.pvp = False
        self.team_pvp = False
        self.issues: set[str] = {"sa_unvalidated"}

    def start_run(self, name="", *, pvp=False, team_pvp=True):
        if self.active:
            raise ValueError("An instance is already being measured")
        self.run_id = uuid4().hex
        self.run_name = name.strip()[:120]
        self.encounters = []
        self.current = None
        self.boss = None
        self.active = True
        self.map_id = None
        self.pvp = pvp is True
        self.team_pvp = self.pvp and team_pvp is True
        self.issues = {"sa_unvalidated"}
        if self.pvp:
            self.issues.add("pvp_experimental")

    def mark_partial(self, reason):
        self.issues.add(reason)
        if self.current:
            self.current.issues.add(reason)

    def finish_encounter(self, result="manual", time_ms=None):
        if self.current:
            self.current.end = max(self.current.start, self.last_time if time_ms is None else time_ms)
            self.current.result = result
            self.current = None

    def stop_run(self, result="manual"):
        self.finish_encounter(result)
        self.active = False

    def select_boss(self, entity_id):
        self.boss = entity_id
        if self.current:
            self.current.boss = entity_id

    def process(self, message):
        """Only the versioned helper's normalized contract is accepted."""
        if message.get("type") != "event":
            return
        session = message.get("session")
        sequence = message.get("sequence")
        timestamp = message.get("time_ms")
        payload = message.get("payload")
        if not isinstance(session, str) or not session or type(sequence) is not int or sequence < 1:
            raise ValueError("Invalid event identity")
        if type(timestamp) is not int or timestamp < 0 or not isinstance(payload, dict):
            raise ValueError("Invalid event envelope")
        if session != self.capture_session:
            if self.capture_session:
                self.finish_encounter("interrupted")
                self.entities = {}
                self.roster = set()
                self.roster_jobs = {}
                self.roster_complete = False
                self.local_id = 0
                self.mark_partial("reconnected")
            self.capture_session, self.last_sequence = session, 0
            self.last_time = 0
        if sequence <= self.last_sequence:
            return  # retransmitted IPC event, not equal-valued legitimate hits
        if sequence != self.last_sequence + 1:
            self.mark_partial("event_gap")
        self.last_sequence = sequence
        self.last_time = max(self.last_time, timestamp)
        kind = message.get("kind")

        def entity_id(key):
            value = payload.get(key, 0)
            if type(value) is not int or not 0 < value <= 0xFFFFFFFF:
                raise ValueError("Invalid entity id")
            return value

        if kind in ("PlayerSeenEvent", "SelfIdentifiedEvent", "NpcSeenEvent", "SummonSeenEvent"):
            actor = entity_id("ActorId")
            if actor not in self.entities and len(self.entities) >= self.MAX_ENTITIES:
                self.mark_partial("entity_limit")
                return
            old = self.entities.get(actor)
            if kind in ("PlayerSeenEvent", "SelfIdentifiedEvent"):
                name = payload.get("Name", "")
                server = payload.get("ServerId", 0)
                if not isinstance(name, str) or len(name) > 100 or type(server) is not int:
                    raise ValueError("Invalid player identity")
                job = self.normalized_class(payload.get("Class", 0)) or self.roster_jobs.get((name, server), 0)
                if not job and old and old.kind == "player" and (old.name, old.server) == (name, server):
                    job = old.job
                entity = Entity(actor, name, server, "player", job=job)
                if kind == "SelfIdentifiedEvent":
                    self.local_id = actor
            elif kind == "NpcSeenEvent":
                name = payload.get("Name") or ""
                entity = Entity(actor, str(name)[:100], kind="npc")
            else:
                entity = Entity(actor, kind="summon", owner=int(payload.get("OwnerId", 0)),
                                owner_name=str(payload.get("OwnerName") or "")[:100])
            self.entities[actor] = entity
            if self.current:
                # Do not rewrite historical attribution after an identified id is reused.
                prior = self.current.entities.get(actor)
                if prior and prior.kind != "unknown" and (prior.kind != entity.kind or
                    (prior.kind == "player" and prior.name and prior.name != entity.name)):
                    self.finish_encounter("interrupted")
                    self.mark_partial("entity_reused")
                else:
                    self.current.entities[actor] = entity
                    self.current.local_id = self.local_id
            # A late identity can resolve the immediately closed encounter, but not a reused id.
            elif old is None and self.encounters and self.encounters[-1].end is not None:
                closed = self.encounters[-1]
                if timestamp - closed.end <= 2000 and actor not in closed.entities:
                    closed.entities[actor] = entity
                    closed.local_id = self.local_id
            return
        if kind == "PartyRosterEvent":
            members = payload.get("Members", [])
            if not isinstance(members, list) or len(members) > 100:
                raise ValueError("Invalid group roster")
            complete = payload.get("Complete", True)
            if type(complete) is not bool:
                raise ValueError("Invalid roster completeness")
            self.roster_complete = complete
            self.roster = {(m["Name"], m["ServerId"]) for m in members
                           if isinstance(m, dict) and isinstance(m.get("Name"), str)
                           and type(m.get("ServerId")) is int}
            self.roster_jobs = {(m["Name"], m["ServerId"]): self.normalized_class(m.get("Class", 0))
                                for m in members if isinstance(m, dict) and (m.get("Name"), m.get("ServerId")) in self.roster}
            for actor, entity in list(self.entities.items()):
                member = self._roster_key(entity, self.roster, self.entities)
                job = self.roster_jobs.get(member, 0)
                if entity.kind == "player" and job:
                    updated = replace(entity, job=job)
                    self.entities[actor] = updated
                    if self.current and actor in self.current.entities:
                        self.current.entities[actor] = updated
            if self.current:
                self.current.roster |= self.roster
                self.current.roster_complete = self.roster_complete
            return
        if kind == "ZoneChangedEvent":
            zone = payload.get("MapId")
            if type(zone) is not int or not 0 < zone <= 9_999_999:
                raise ValueError("Invalid map id")
            if self.map_id is not None and zone != self.map_id and not payload.get("IsTeleport"):
                self.finish_encounter("interrupted")
                self.active = False
                self.entities = {}
                # Party membership persists until a roster update; map-local actor ids do not.
                self.local_id = 0
                self.boss = None
            self.map_id = zone
            return
        if kind == "InstanceTimerEvent":
            zone, start, end = (payload.get(key) for key in ("MapId", "StartMs", "EndMs"))
            if (type(zone) is not int or not 0 < zone <= 9_999_999 or type(start) is not int
                or type(end) is not int or start < 1_600_000_000_000 or not 0 < end - start <= 86_400_000):
                raise ValueError("Invalid instance timer")
            return
        if kind == "DeathEvent":
            actor = entity_id("ActorId")
            if self.current and not payload.get("AlreadyDead") and actor == self.current.boss:
                self.finish_encounter("target_defeated", timestamp)
            return
        if kind != "DamageEvent" or not self.active:
            return
        damage = payload.get("Damage")
        if type(damage) is not int or not 0 < damage <= 10**12:
            raise ValueError("Invalid observed damage")
        source, target = entity_id("SourceId"), entity_id("TargetId")
        if source == target:
            return
        source_entity = self.entities.get(source)
        target_entity = self.entities.get(target)
        if source_entity and source_entity.kind == "npc":
            return
        if not self.pvp and target_entity and target_entity.kind in ("player", "summon"):
            return
        encounter = self.current
        if encounter is None and self.encounters:
            previous = self.encounters[-1]
            if (previous.result == "target_defeated" and previous.end is not None and
                timestamp <= previous.end + 1500 and target == previous.boss):
                encounter = previous  # reconcile a late final hit, no new attempt
        if encounter is None:
            encounter = Encounter(start=timestamp, entities=dict(self.entities), roster=set(self.roster),
                                  roster_complete=self.roster_complete, local_id=self.local_id,
                                  boss=self.boss, issues=set(self.issues), pvp=self.pvp, team_pvp=self.team_pvp)
            self.encounters.append(encounter)
            self.current = encounter
        if len(encounter.hits) >= self.MAX_HITS:
            encounter.issues.add("event_limit")
            self.mark_partial("event_limit")
            return
        encounter.hits.append(Hit(timestamp, source, target, damage, int(payload.get("SkillCode", 0))))
        if target_entity is None:
            encounter.issues.add("unknown_target")

    @staticmethod
    def _owner(source, encounter):
        visited = set()
        for _ in range(8):
            if source in visited:
                return None
            visited.add(source)
            entity = encounter.entities.get(source)
            if not entity:
                return None
            if entity.kind == "player":
                return entity
            if entity.kind != "summon":
                return None
            if entity.owner:
                source = entity.owner
                continue
            candidates = [e for e in encounter.entities.values() if e.kind == "player"
                          and e.name and e.name == entity.owner_name]
            return candidates[0] if len(candidates) == 1 else None
        return None

    @staticmethod
    def _roster_key(owner, roster, entities):
        exact = (owner.name, owner.server)
        if exact in roster:
            return exact
        if owner.server or not owner.name:
            return None
        matches = [key for key in roster if key[0] == owner.name]
        peers = [entity for entity in entities.values()
                 if entity.kind == "player" and entity.name == owner.name and entity.id != owner.id]
        return matches[0] if len(matches) == 1 and not peers else None

    @staticmethod
    def _pvp_friendly(owner, encounter):
        return owner.id == encounter.local_id or (
            encounter.team_pvp and
            CombatEngine._roster_key(owner, encounter.roster, encounter.entities) is not None
        )

    def snapshot(self, scope="encounter", boss_only=False, encounter_id=None):
        selected = self.encounters if scope == "instance" else [next((e for e in reversed(self.encounters)
                    if encounter_id is None or e.id == encounter_id), None)]
        selected = [e for e in selected if e is not None]
        totals = {}
        unknown = 0
        duration_ms = 0
        issues = set(self.issues)
        if self.team_pvp and not selected and (not self.roster or not self.roster_complete):
            issues.add("missing_roster")
        for encounter in selected:
            issues |= encounter.issues
            end = encounter.end if encounter.end is not None else self.last_time
            duration_ms += max(0, end - encounter.start)
            if not encounter.roster or not encounter.roster_complete:
                issues.add("missing_roster")
            for hit in encounter.hits:
                actor = encounter.entities.get(hit.source)
                target = encounter.entities.get(hit.target)
                if actor and actor.kind == "npc":
                    continue
                if not encounter.pvp and target and target.kind in ("player", "summon"):
                    continue
                if encounter.pvp:
                    attacker = self._owner(hit.source, encounter)
                    if attacker is None:
                        # An unknown source may be an opponent; never add it to our team's total.
                        issues.add("unattributed")
                        continue
                    if not self._pvp_friendly(attacker, encounter):
                        continue
                    if target is None or target.kind == "unknown":
                        issues.add("unknown_target")
                        continue
                    if target.kind in ("player", "summon"):
                        defender = self._owner(hit.target, encounter)
                        if defender is None:
                            issues.add("unknown_target")
                            continue
                        if self._pvp_friendly(defender, encounter):
                            continue
                if boss_only and scope != "instance":
                    if encounter.boss is None:
                        issues.add("missing_target")
                        continue
                    if hit.target != encounter.boss:
                        continue
                owner = self._owner(hit.source, encounter)
                if owner is None:
                    unknown += hit.damage
                    continue
                member = self._roster_key(owner, encounter.roster, encounter.entities)
                if owner.id != encounter.local_id and member is None:
                    matching_name = any(name == owner.name for name, _ in encounter.roster)
                    if encounter.roster_complete and (owner.server or not matching_name):
                        continue  # observed non-member, never rank them in our group
                    unknown += hit.damage
                    continue
                key = member or ((owner.name, owner.server) if owner.name else ("", owner.id))
                row = totals.setdefault(key, {"name": owner.name, "server": owner.server, "actor_id": owner.id,
                        "job": owner.job, "local": False, "damage": 0})
                row["damage"] += hit.damage
                if owner.job:
                    row["job"] = owner.job
                row["local"] |= owner.id == encounter.local_id
        total = unknown + sum(row["damage"] for row in totals.values())
        rows = sorted(totals.values(), key=lambda r: (-r["damage"], r["name"], r["server"], r["actor_id"]))
        last_damage = None
        rank = 0
        for index, row in enumerate(rows, 1):
            if row["damage"] != last_damage:
                rank = index
            last_damage = row["damage"]
            row.update(rank=rank, share=row["damage"] / total if total else 0,
                       dps=row["damage"] * 1000 / duration_ms if duration_ms else None)
        if unknown:
            issues.add("unattributed")
        return {"run_id": self.run_id, "run_name": self.run_name, "scope": scope, "boss_only": boss_only,
                "encounter_id": selected[-1].id if len(selected) == 1 else None,
                "result": selected[-1].result if selected else "waiting", "duration_ms": duration_ms,
                "total": total, "unattributed": unknown, "rows": rows, "issues": sorted(issues),
                "active": self.active, "encounters": len(self.encounters),
                "pvp": selected[-1].pvp if selected else self.pvp,
                "team_pvp": selected[-1].team_pvp if selected else self.team_pvp}
