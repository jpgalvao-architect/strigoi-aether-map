# SPDX-License-Identifier: GPL-3.0-only
"""Public endpoint, invite and preset validation for the Live Sync v1 wire protocol."""
import hashlib
import hmac
import json
import re
from dataclasses import dataclass

from app.modules.siege.models import Preset

MAX_BYTES = 512 * 1024
KEY = re.compile(r'[a-f0-9]{64}')
SESSION_ID = re.compile(r'[a-f0-9]{32}')
DOMAIN_LABEL = r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?'
ENDPOINT = re.compile(rf'https://{DOMAIN_LABEL}\.{DOMAIN_LABEL}\.workers\.dev')
INVITE_PREFIX = 'azphelumbra-live:v1:'


def endpoint_url(value):
    endpoint = value.strip().lower().removesuffix('/')
    if not ENDPOINT.fullmatch(endpoint):
        raise ValueError('Use o endereço HTTPS do Worker terminado em .workers.dev.')
    return endpoint


@dataclass(frozen=True, repr=False)
class Invite:
    endpoint: str
    session: str
    reader: str

    def encode(self):
        return f'{INVITE_PREFIX}{self.endpoint}#{self.session}.{self.reader}'

    @classmethod
    def parse(cls, text):
        text = text.strip()
        if not text.startswith(INVITE_PREFIX) or len(text) > 256:
            raise ValueError('Convite do Live Sync inválido.')
        try:
            endpoint, identity = text[len(INVITE_PREFIX):].split('#')
            session, reader = identity.split('.')
            if SESSION_ID.fullmatch(session) and KEY.fullmatch(reader):
                return cls(endpoint_url(endpoint), session, reader)
        except ValueError:
            pass
        raise ValueError('Convite do Live Sync inválido.')


def sign(key, message):
    return hmac.new(key.encode('ascii'), message.encode('ascii'), hashlib.sha256).hexdigest()


def digest(body):
    return hashlib.sha256(body).hexdigest()


def snapshot_bytes(preset):
    return json.dumps(preset.model_dump(mode='json'), sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


class IncompatibleCatalogue(ValueError):
    pass


def read_snapshot(body):
    if len(body) > MAX_BYTES:
        raise ValueError
    fields = json.loads(body.decode('utf-8'))
    catalogue = fields.get('ring_catalogue') if isinstance(fields, dict) else None
    if isinstance(catalogue, dict) and catalogue.get('version') != 1:
        raise IncompatibleCatalogue
    if (not isinstance(fields, dict) or fields.get('schema_version') != 3
            or fields.get('map_id') != 'lower-reshanta' or not {'markers', 'drawings'} <= fields.keys()
            or not isinstance(fields.get('name'), str) or not fields['name'].strip().isprintable()):
        raise ValueError
    return Preset.model_validate(fields)


def version_notice(data):
    version, checksum = data.get('version'), data.get('hash')
    if (type(version) is not int or not 0 <= version <= 9_999_999_999
            or (version == 0 and checksum is not None)
            or (version > 0 and (not isinstance(checksum, str) or not KEY.fullmatch(checksum)))):
        raise ValueError
    return version, checksum
