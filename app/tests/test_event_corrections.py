# SPDX-License-Identifier: GPL-3.0-only
import json
from datetime import UTC, datetime
from app.core.models import EventFeed, GameEvent
from app.infrastructure.storage import PACKAGE, atomic_json, load_model
from app.modules.events.service import occurrences, countdown, display_time
from app.modules.events.corrections import correct_bundled_schedules
from app.services.context import AppContext


def original_rule():
    manifest = json.loads((PACKAGE / "data/event-schedule-corrections.json").read_text(encoding="utf-8"))
    data = dict(manifest["corrections"][0]["replacement"])
    data.update(verified_on="2026-10-11", verification="Reprodução factual da agenda publicada, sem confirmação no servidor",
                notes="Perfil do projeto consultado. Relógio da regra: UTC. Horários podem divergir da agenda anterior.")
    data["schedule"] = dict(data["schedule"], timezone="UTC")
    return GameEvent.model_validate(data), manifest


def test_sa_siege_stays_at_21_local_with_different_display_timezones():
    feed = load_model(PACKAGE / "data/events.json", EventFeed)
    siege = next(e for e in feed.events if e.id == "reference-sa-artifact-siege")
    now = datetime(2026, 10, 12, 20, 57, 57, tzinfo=UTC)
    upcoming = occurrences([siege], now)[0]
    assert upcoming.starts_at == datetime(2026, 10, 13, 0, tzinfo=UTC)
    assert countdown(upcoming.starts_at, now) == "03:02:03"
    assert "21:00" in display_time(upcoming.starts_at, "America/Sao_Paulo")
    assert "00:00" in display_time(upcoming.starts_at, "UTC")


def test_clock_migration_preserves_custom_rules_and_disabled_event(qapp, tmp_path):
    original, manifest = original_rule()
    original.enabled = False
    feed = EventFeed(demo=False, events=[original])
    fixed, changed = correct_bundled_schedules(feed, manifest)
    assert changed == [original.id] and not fixed.events[0].enabled
    assert fixed.events[0].schedule.timezone == "America/Sao_Paulo"
    custom = original.model_copy(deep=True)
    custom.schedule.times = ["22:00"]
    assert correct_bundled_schedules(EventFeed(demo=False, events=[custom]), manifest)[1] == []
    atomic_json(tmp_path / "events-cache.json", feed)
    context = AppContext(tmp_path)
    assert context.feed.events[0].schedule.timezone == "America/Sao_Paulo"
    assert not context.feed.events[0].enabled
    assert load_model(tmp_path / "events-cache.siege-v030-backup.json", EventFeed) == feed
    assert AppContext(tmp_path).feed == context.feed
