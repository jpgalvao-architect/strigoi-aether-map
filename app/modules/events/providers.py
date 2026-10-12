# SPDX-License-Identifier: GPL-3.0-only
"""Providers return validated data; failed refreshes never replace a valid cache."""
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.core.models import EventFeed
from app.infrastructure.storage import atomic_json, load_model


class EventProvider(Protocol):
    def load(self) -> EventFeed: ...


class LocalJsonProvider:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> EventFeed:
        return load_model(self.path, EventFeed)


class HttpsOnlyRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme != "https":
            raise ValueError("Redirecionamento não HTTPS recusado")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class RemoteJsonProvider:
    def __init__(self, url: str):
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Informe uma URL HTTPS sem credenciais")
        self.url = url

    def load(self) -> EventFeed:
        request = Request(self.url, headers={"User-Agent": "StrigoiAetherMap/0.1", "Accept": "application/json"})
        with build_opener(HttpsOnlyRedirect()).open(request, timeout=10) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Feed excede 2 MB")
        return EventFeed.model_validate_json(raw)


def refresh_cache(provider: EventProvider, cache: Path) -> EventFeed:
    feed = provider.load()
    atomic_json(cache, feed)
    return feed
