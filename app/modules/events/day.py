# SPDX-License-Identifier: GPL-3.0-only
"""Calendar-day events in the user's display timezone, including earlier starts."""
from datetime import UTC,datetime,time,timedelta
from zoneinfo import ZoneInfo
from app.modules.events.service import occurrences


def local_time(instant,timezone):
    return instant.astimezone() if timezone=='local' else instant.astimezone(ZoneInfo(timezone))


def day_events(events,now,timezone):
    local=local_time(now,timezone)
    zone=None if timezone=='local' else local.tzinfo
    start=datetime.combine(local.date(),time.min,zone).astimezone(UTC)
    end=datetime.combine(local.date()+timedelta(days=1),time.min,zone).astimezone(UTC)
    return [item for item in occurrences(events,start,days=2) if start<=item.starts_at<end]
