# SPDX-License-Identifier: GPL-3.0-only
"""Replace only identified bundled rules; custom schedules remain untouched."""
import hashlib
import json
from app.core.models import GameEvent


def correct_bundled_schedules(feed, manifest):
    replacements = {item["id"]: item for item in manifest["corrections"]}
    events, changed = [], []
    for event in feed.events:
        rule = replacements.get(event.id)
        fingerprint = hashlib.sha256(json.dumps(event.model_dump(mode="json", exclude={"enabled"}),
                                                sort_keys=True, ensure_ascii=True).encode()).hexdigest()
        if rule and fingerprint == rule["old_sha256"]:
            replacement = GameEvent.model_validate(rule["replacement"])
            events.append(replacement.model_copy(update={"enabled": event.enabled}))
            changed.append(event.id)
        else:
            events.append(event)
    return feed.model_copy(update={"events": events}), changed
