# SPDX-License-Identifier: GPL-3.0-only
from datetime import UTC, datetime, timedelta
import json

import pytest
from pydantic import ValidationError

from app.core.models import Dataset, EventFeed, EventSchedule, GameEvent, NotificationSettings, Preferences
from app.infrastructure.storage import atomic_json, load_model, recover_model, resolve_map_image
from app.modules.events.service import Occurrence, countdown, display_time, occurrences
from app.modules.events.providers import RemoteJsonProvider, refresh_cache
from app.modules.gatherables.service import FilterQuery, filter_points
from app.modules.notifications.service import AlertEngine


def event(**schedule):
    return GameEvent(id="test", name="Test event", kind="Siege", region="demo", source="test", schedule=EventSchedule(**schedule))


def test_seed_integrity(dataset, feed):
    assert len(dataset.all_points) == 90
    assert len(dataset.cubes) == 10
    assert len(dataset.categories) == 7
    assert all(resolve_map_image(m.image).is_file() for m in dataset.maps)
    assert dataset.demo and feed.demo


@pytest.mark.parametrize("change", ["coordinate", "resource", "duplicate", "map", "subcategory"])
def test_invalid_dataset_rejected(dataset, change):
    data = dataset.model_dump()
    if change == "coordinate":
        data["points"][0]["x"] = 1.1
    elif change == "resource":
        data["points"][0]["resource_id"] = "missing"
    elif change == "duplicate":
        data["cubes"][0]["id"] = data["points"][0]["id"]
    elif change == "map":
        data["maps"] = []
    else:
        data["resources"][0]["subcategory"] = data["resources"][1]["subcategory"]
    with pytest.raises(ValidationError):
        Dataset.model_validate(data)


def test_combined_filters_and_overlay(dataset):
    prefs = Preferences()
    prefs.disabled_categories.add("ore")
    prefs.disabled_resources.add("azpha")
    result = filter_points(dataset, prefs, FilterQuery(map_id="vale-lunar"))
    resources = {r.id: r for r in dataset.resources}
    assert result and all(p.map_id == "vale-lunar" and resources[p.resource_id].category != "ore" and p.resource_id != "azpha" for p in result)
    point = result[0]
    point.visible_in_overlay = False
    assert point not in filter_points(dataset, prefs, FilterQuery(overlay=True))
    prefs.visited.add(point.id)
    prefs.hide_visited = True
    assert point not in filter_points(dataset, prefs, FilterQuery())


def test_cube_and_search_filters(dataset):
    points = filter_points(dataset, Preferences(), FilterQuery(cubes_only=True, search="CUBO", rarity="epic"))
    assert len(points) == 10
    assert not filter_points(dataset, Preferences(), FilterQuery(subcategory="missing"))
    assert filter_points(dataset, Preferences(), FilterQuery(resource_id="azpha"))


def test_daily_source_timezone_and_midnight():
    now = datetime(2026, 10, 11, 23, 59, tzinfo=UTC)
    results = occurrences([event(timezone="Asia/Seoul", times=["09:00"])], now, days=1)
    assert results[0].starts_at == datetime(2026, 10, 12, tzinfo=UTC)
    assert "21:00" in display_time(results[0].starts_at, "America/Fortaleza")


def test_weekly_and_disabled():
    now = datetime(2026, 10, 11, tzinfo=UTC)  # Sunday
    weekly = event(recurrence="weekly", weekdays=[0], times=["12:00"])
    assert occurrences([weekly], now)[0].starts_at.weekday() == 0
    weekly.enabled = False
    assert not occurrences([weekly], now)


def test_dst_gap_skipped_and_fold_once():
    spring = event(timezone="America/New_York", times=["02:30"])
    assert not occurrences([spring], datetime(2026, 3, 8, 5, tzinfo=UTC), days=1)
    autumn = event(timezone="America/New_York", times=["01:30"])
    result = occurrences([autumn], datetime(2026, 11, 1, 4, tzinfo=UTC), days=1)
    assert len(result) == 1
    assert result[0].starts_at.hour == 5


def test_once_and_aware_contract():
    with pytest.raises(ValidationError):
        EventSchedule(recurrence="once", starts_at=datetime(2026, 1, 1))
    one = event(recurrence="once", starts_at=datetime(2026, 10, 12, tzinfo=UTC))
    assert len(occurrences([one], datetime(2026, 10, 11, tzinfo=UTC))) == 1
    assert not occurrences([one], datetime(2026, 10, 13, tzinfo=UTC))
    with pytest.raises(ValueError):
        occurrences([one], datetime(2026, 10, 11))


@pytest.mark.parametrize("data", [{"timezone":"No/Zone"},{"times":["25:00"]},{"weekdays":[7]},{"times":["12:00","12:00"]}])
def test_bad_schedules(data):
    with pytest.raises(ValidationError):
        EventSchedule(**data)


def test_countdown():
    now = datetime.now(UTC)
    assert countdown(now-timedelta(seconds=5), now) == "00:00:00"
    assert countdown(now+timedelta(days=2, hours=3, minutes=4, seconds=5), now) == "2d 03:04:05"


def test_alert_dedup_survives_restart(tmp_path):
    now = datetime(2026, 10, 11, 12, tzinfo=UTC)
    item = Occurrence(event(), now+timedelta(minutes=5))
    engine = AlertEngine(tmp_path / "alerts.json")
    settings = NotificationSettings()
    assert engine.due([item], settings, now) == [(item, 5)]
    assert not engine.due([item], settings, now+timedelta(seconds=1))
    assert not AlertEngine(engine.path).due([item], settings, now+timedelta(seconds=2))


def test_alert_preferences_and_no_late_flood(tmp_path):
    now = datetime(2026, 10, 11, 12, tzinfo=UTC)
    item = Occurrence(event(), now+timedelta(minutes=3))
    engine = AlertEngine(tmp_path / "alerts.json")
    assert not engine.due([item], NotificationSettings(), now)
    item = Occurrence(event(), now+timedelta(minutes=5))
    assert not engine.due([item], NotificationSettings(disabled_kinds={"Siege"}), now)
    assert not engine.due([item], NotificationSettings(enabled=False), now)


def test_preferences_roundtrip_and_corruption_recovery(tmp_path):
    path = tmp_path / "prefs.json"
    prefs = Preferences(disabled_resources={"azpha"}, visited={"cube-1"})
    atomic_json(path, prefs)
    assert load_model(path, Preferences) == prefs
    path.write_text('{"broken":', encoding="utf-8")
    recovered, warning = recover_model(path, Preferences, Preferences())
    assert warning and recovered == Preferences()
    assert list(tmp_path.glob("prefs.invalid-*.json"))


def test_failed_provider_keeps_cache(tmp_path, feed):
    path = tmp_path / "feed.json"
    atomic_json(path, feed)
    previous = path.read_bytes()
    class Broken:
        def load(self):
            raise OSError("offline")
    with pytest.raises(OSError):
        refresh_cache(Broken(), path)
    assert path.read_bytes() == previous


@pytest.mark.parametrize("url", ["http://example.com", "file:///tmp/events.json", "https://user:pass@example.com", "invalid"])
def test_https_only(url):
    with pytest.raises(ValueError):
        RemoteJsonProvider(url)


def test_path_traversal_rejected():
    with pytest.raises(ValueError):
        resolve_map_image("../../secrets.json")
