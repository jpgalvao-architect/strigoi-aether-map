# SPDX-License-Identifier: GPL-3.0-only
"""Validated data contract. Coordinates use [0, 1], origin at the top left."""
from datetime import datetime, time
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Region(Model):
    id: str
    name: str
    description: str = ""


class MapDefinition(Model):
    id: str
    name: str
    region: str
    image: str
    width: int = Field(default=1200, ge=100, le=16000)
    height: int = Field(default=800, ge=100, le=16000)
    source: str
    supports_overlay: bool = True


class Category(Model):
    id: str
    name: str
    icon: Literal["diamond", "circle", "leaf", "wood", "star", "cube", "pets"] = "circle"
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")


class Subcategory(Model):
    id: str
    category: str
    name: str


class Gatherable(Model):
    id: str
    name: str
    category: str
    subcategory: str
    rarity: Literal["common", "uncommon", "rare", "epic", "unknown"] = "unknown"
    notes: str = ""
    source: str = ""
    verification: str = "Não informada"


class PointOfInterest(Model):
    id: str
    name: str
    map_id: str
    resource_id: str
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    enabled: bool = True
    notes: str = ""
    source: str
    visible_in_overlay: bool = True
    certainty: Literal["confirmed", "possible", "demo"] = "demo"


class HiddenCube(PointOfInterest):
    """Cube-specific fields without coupling the renderer to a resource type."""
    underwater: bool | None = None
    route_hint: str = ""


class EventSchedule(Model):
    timezone: str = "UTC"
    recurrence: Literal["once", "daily", "weekly"] = "daily"
    times: list[str] = Field(default_factory=lambda: ["20:00"])
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)))
    starts_at: datetime | None = None

    @field_validator("timezone")
    @classmethod
    def timezone_exists(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (KeyError, ValueError) as exc:
            raise ValueError("Timezone IANA inválido") from exc
        return value

    @field_validator("times")
    @classmethod
    def valid_times(cls, values: list[str]) -> list[str]:
        if not values or len(values) != len(set(values)):
            raise ValueError("Horários vazios ou duplicados")
        for value in values:
            parsed = time.fromisoformat(value)
            if len(value) != 5 or parsed.tzinfo or parsed.second:
                raise ValueError("Use HH:MM")
        return sorted(values)

    @field_validator("weekdays")
    @classmethod
    def valid_days(cls, values: list[int]) -> list[int]:
        if not values or any(day < 0 or day > 6 for day in values):
            raise ValueError("Dias da semana: 0 a 6")
        return sorted(set(values))

    @model_validator(mode="after")
    def once_requires_timestamp(self):
        if self.recurrence == "once" and (
            self.starts_at is None or self.starts_at.utcoffset() is None
        ):
            raise ValueError("Evento único exige starts_at com fuso")
        return self


class GameEvent(Model):
    id: str
    name: str
    kind: str
    region: str
    schedule: EventSchedule
    source: str
    notes: str = ""
    enabled: bool = True
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    verified_on: str = ""
    verification: str = "Não informada"


class EventFeed(Model):
    schema_version: Literal[1] = 1
    demo: bool = True
    events: list[GameEvent]
    release: str = ""
    coverage: str = ""

    @model_validator(mode="after")
    def unique_ids(self):
        if len({e.id for e in self.events}) != len(self.events):
            raise ValueError("IDs de evento duplicados")
        return self


class Dataset(Model):
    schema_version: Literal[1] = 1
    demo: bool = True
    title: str
    release: str = ""
    coverage: str = ""
    checked_on: str = ""
    regions: list[Region]
    maps: list[MapDefinition]
    categories: list[Category]
    subcategories: list[Subcategory]
    resources: list[Gatherable]
    points: list[PointOfInterest]
    cubes: list[HiddenCube] = Field(default_factory=list)

    @model_validator(mode="after")
    def references_exist(self):
        groups = [self.regions, self.maps, self.categories, self.subcategories, self.resources,
                  [*self.points, *self.cubes]]
        for group in groups:
            if len({item.id for item in group}) != len(group):
                raise ValueError("IDs duplicados no dataset")
        regions = {v.id for v in self.regions}
        maps = {v.id for v in self.maps}
        categories = {v.id for v in self.categories}
        subcategories = {v.id: v for v in self.subcategories}
        resources = {v.id for v in self.resources}
        if not self.maps:
            raise ValueError("Dataset precisa ter ao menos um mapa")
        for item in self.maps:
            if item.region not in regions:
                raise ValueError(f"Região inexistente: {item.region}")
        for sub in self.subcategories:
            if sub.category not in categories:
                raise ValueError(f"Categoria inexistente: {sub.category}")
        for resource in self.resources:
            sub = subcategories.get(resource.subcategory)
            if resource.category not in categories or not sub or sub.category != resource.category:
                raise ValueError(f"Categoria/subcategoria inválida: {resource.id}")
        for point in [*self.points, *self.cubes]:
            if point.map_id not in maps or point.resource_id not in resources:
                raise ValueError(f"Referência inválida: {point.id}")
        return self

    @property
    def all_points(self) -> list[PointOfInterest]:
        return [*self.points, *self.cubes]


class NotificationSettings(Model):
    enabled: bool = True
    lead_minutes: list[int] = Field(default_factory=lambda: [5, 15])
    disabled_kinds: set[str] = Field(default_factory=set)

    @field_validator("lead_minutes")
    @classmethod
    def supported_leads(cls, value: list[int]) -> list[int]:
        if any(v not in (5, 15, 30) for v in value):
            raise ValueError("Antecedências suportadas: 5, 15, 30")
        return sorted(set(value))


class OverlaySettings(Model):
    enabled: bool = False
    opacity: float = Field(default=0.8, ge=0.1, le=1)
    scale: float = Field(default=1.0, ge=0.5, le=3)
    threshold: float = Field(default=0.96, ge=0.8, le=1)
    monitor: int = Field(default=1, ge=1, le=16)
    map_id: str = "altgard"
    calibration: str = ""
    capture_area: str = ""
    tracking_mode: Literal["dynamic", "fixed"] = "dynamic"
    minimum_matches: int = Field(default=18, ge=12, le=80)
    events_panel: bool = False
    events_panel_expanded: bool = False
    events_panel_position: tuple[int, int] | None = None
    events_panel_event: str = ""
    layers: Literal["atlas", "cubes", "gathering", "all"] = "atlas"
    map_view: Literal["large", "minimap"] = "large"
    minimap_area: str = ""
    render_hz: Literal[60, 120, 240] = 240
    capture_hz: int = Field(default=60, ge=10, le=60)


class CombatSettings(Model):
    auto_capture: bool = True
    panel_visible: bool = True
    panel_mode_release: str = ""
    locked: bool = True
    opacity: float = Field(default=0.9, ge=0.2, le=1)
    position: tuple[int, int] | None = None
    size: tuple[int, int] | None = None

    @field_validator("size")
    @classmethod
    def valid_size(cls, value):
        if value is not None and not (360 <= value[0] <= 3840 and 180 <= value[1] <= 2160):
            raise ValueError("Invalid combat panel size")
        return value


class QuickMenuSettings(Model):
    enabled: bool = True
    position: tuple[int, int] | None = None


class PetSettings(Model):
    map_filter: Literal['all', 'favorites', 'needed'] = 'all'
    focus_id: int | None = Field(default=None, gt=0)
    layer_release: str = ''
    panel_visible: bool = False
    panel_expanded: bool = False
    panel_position: tuple[int, int] | None = None
    auto_collection: bool = True
    region: Literal['sa', 'eu', 'nae', 'naw', 'asia', 'kr', 'tw'] = 'sa'


class Preferences(Model):
    schema_version: Literal[1] = 1
    ui_language: Literal['pt_BR','en_US'] | None = None
    timezone: str = "local"
    content_release: str = ""
    cube_data_release: str = ""
    map_id: str = "altgard"
    catalog_map_id: str = "altgard"
    map_defaults_release: str = ""
    agenda_profile: str = "reference-sa"
    disabled_categories: set[str] = Field(default_factory=set)
    disabled_resources: set[str] = Field(default_factory=set)
    visited: set[str] = Field(default_factory=set)
    hide_visited: bool = False
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    overlay: OverlaySettings = Field(default_factory=OverlaySettings)
    combat: CombatSettings = Field(default_factory=CombatSettings)
    quick_menu: QuickMenuSettings = Field(default_factory=QuickMenuSettings)
    pets: PetSettings = Field(default_factory=PetSettings)
    remote_events_url: str = ""
    remote_auto_refresh: bool = False
    remote_interval_minutes: int = Field(default=30, ge=5, le=1440)
    sonar_enabled: bool = False
    sonar_process_name: str = ""
    sonar_sensitivity: Literal["balanced", "sensitive"] = "balanced"
    sonar_alert_position: tuple[int, int] | None = None
    overlay_layers_release: str = ""

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        if value != "local":
            EventSchedule.timezone_exists(value)
        return value
