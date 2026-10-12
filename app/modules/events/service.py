# SPDX-License-Identifier: GPL-3.0-only
"""Offline scheduling in source timezones, returning timezone-aware UTC instants."""
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.models import GameEvent


@dataclass(frozen=True)
class Occurrence:
    event: GameEvent
    starts_at: datetime

    @property
    def key(self) -> str:
        return f"{self.event.id}@{self.starts_at.isoformat()}"


def occurrences(events: list[GameEvent], now: datetime, days: int = 8) -> list[Occurrence]:
    if now.utcoffset() is None:
        raise ValueError("now precisa incluir timezone")
    now = now.astimezone(UTC)
    until = now + timedelta(days=days)
    result = []
    for event in events:
        if not event.enabled:
            continue
        schedule = event.schedule
        if schedule.recurrence == "once":
            instant = schedule.starts_at.astimezone(UTC)
            if now <= instant < until:
                result.append(Occurrence(event, instant))
            continue
        zone = ZoneInfo(schedule.timezone)
        first = now.astimezone(zone).date()
        for offset in range(days + 2):
            date = first + timedelta(days=offset)
            if schedule.recurrence == "weekly" and date.weekday() not in schedule.weekdays:
                continue
            for clock in schedule.times:
                local = datetime.combine(date, time.fromisoformat(clock), zone)
                instant = local.astimezone(UTC)
                # Nonexistent DST wall times are skipped; ambiguous times use fold=0 once.
                if instant.astimezone(zone).replace(tzinfo=None) != local.replace(tzinfo=None):
                    continue
                if now <= instant < until:
                    result.append(Occurrence(event, instant))
    return sorted(result, key=lambda item: (item.starts_at, item.event.id))


def display_time(instant: datetime, timezone: str) -> str:
    from app.core.i18n import calendar_date, clock
    converted = instant.astimezone() if timezone == "local" else instant.astimezone(ZoneInfo(timezone))
    offset = converted.strftime("%z")
    compact_zone = f"UTC{offset[:3]}:{offset[3:]}"
    return calendar_date(converted)+" • "+clock(converted)+" "+compact_zone


def countdown(instant: datetime, now: datetime) -> str:
    seconds = max(0, int((instant - now).total_seconds()))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return (f"{days}d " if days else "") + f"{hours:02}:{minutes:02}:{seconds:02}"
