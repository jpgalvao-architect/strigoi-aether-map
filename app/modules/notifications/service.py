# SPDX-License-Identifier: GPL-3.0-only
"""Persistent, bounded alert ledger. Only due transitions emit notifications."""
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.models import Model, NotificationSettings
from app.infrastructure.storage import atomic_json, recover_model
from app.modules.events.service import Occurrence
from pydantic import Field


class AlertLedger(Model):
    sent: dict[str, float] = Field(default_factory=dict)


class AlertEngine:
    def __init__(self, path: Path):
        self.path = path
        self.ledger, _ = recover_model(path, AlertLedger, AlertLedger())
        self.last_check: datetime | None = None

    def due(self, items: list[Occurrence], settings: NotificationSettings, now: datetime) -> list[tuple[Occurrence, int]]:
        # On startup/resume, a 90-second grace avoids flooding for missed alerts.
        lower = max(self.last_check or now - timedelta(seconds=90), now - timedelta(seconds=90))
        if lower > now:
            lower = now - timedelta(seconds=90)
        self.last_check = now
        if not settings.enabled:
            return []
        due = []
        for item in items:
            if item.event.kind in settings.disabled_kinds or item.starts_at <= now:
                continue
            for lead in settings.lead_minutes:
                trigger = item.starts_at - timedelta(minutes=lead)
                key = f"{item.key}/{lead}"
                if lower <= trigger <= now and key not in self.ledger.sent:
                    due.append((item, lead))
                    self.ledger.sent[key] = now.timestamp()
        cutoff = (now.astimezone(UTC) - timedelta(days=14)).timestamp()
        old_count = len(self.ledger.sent)
        self.ledger.sent = {key: stamp for key, stamp in self.ledger.sent.items() if stamp >= cutoff}
        if due or old_count != len(self.ledger.sent):
            atomic_json(self.path, self.ledger)
        return due
