# SPDX-License-Identifier: GPL-3.0-only
"""Atomic local persistence, with recovery that preserves damaged input."""
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
log = logging.getLogger(__name__)
PACKAGE = Path(__file__).resolve().parents[1]


def user_data_dir() -> Path:
    override = os.environ.get("STRIGOI_DATA_DIR")
    base = Path(override) if override else Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local/share"))) / "StrigoiAetherMap"
    base.mkdir(parents=True, exist_ok=True)
    return base


def atomic_json(path: Path, value: BaseModel | dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = value.model_dump_json(indent=2) if isinstance(value, BaseModel) else json.dumps(value, indent=2, ensure_ascii=False)
    descriptor, temporary = tempfile.mkstemp(prefix=path.stem, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_model(path: Path, model: type[T]) -> T:
    limit = 12_000_000 if model.__name__ == 'Dataset' else 5_000_000
    if path.stat().st_size > limit:
        raise ValueError(f"JSON excede o limite de {limit // 1_000_000} MB")
    return model.model_validate_json(path.read_text(encoding="utf-8-sig"))


def recover_model(path: Path, model: type[T], fallback: T) -> tuple[T, str]:
    if not path.exists():
        return fallback, ""
    try:
        return load_model(path, model), ""
    except (ValueError, OSError):
        backup = path.with_suffix(f".invalid-{datetime.now():%Y%m%d-%H%M%S-%f}.json")
        log.exception("Falha ao ler %s", path.name)
        try:
            path.replace(backup)
        except OSError:
            log.exception("Não foi possível preservar arquivo inválido")
        return fallback, f"{path.name} inválido; usando configuração padrão. Consulte os logs."


def resolve_map_image(image: str) -> Path:
    """Only bundled assets or explicitly imported local raster files are accepted."""
    path = Path(image)
    if path.is_absolute():
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            raise ValueError("Mapas externos devem ser PNG/JPG")
        return path
    resolved = (PACKAGE / "assets" / image).resolve()
    if not resolved.is_relative_to((PACKAGE / "assets").resolve()):
        raise ValueError("Caminho de mapa fora da pasta assets")
    return resolved
