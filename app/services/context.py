# SPDX-License-Identifier: GPL-3.0-only
"""Application state shared by UI modules, with one persistence boundary."""
import logging
import hashlib
import shutil
import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.core.models import Dataset, EventFeed, Preferences
from app.infrastructure.storage import PACKAGE, atomic_json, load_model, recover_model, resolve_map_image
from app.modules.notifications.service import AlertEngine


class AppContext(QObject):
    changed = Signal()
    events_changed = Signal()
    error = Signal(str)

    def __init__(self, directory: Path):
        super().__init__()
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.messages: list[str] = []
        self.prefs, warning = recover_model(directory / "preferences.json", Preferences, load_model(PACKAGE / "config/defaults.json", Preferences))
        if self.prefs.ui_language is None:
            try:
                seed=json.loads((directory/'installation.json').read_text(encoding='utf-8-sig'))
                selected=seed.get('default_language','pt_BR')
            except (OSError,ValueError,AttributeError):
                selected='pt_BR'
            self.prefs.ui_language=selected if selected in ('pt_BR','en_US') else 'pt_BR'
        if warning:
            self.messages.append(warning)
        # Consent is session-scoped. A saved configuration never starts capture on launch.
        self.prefs.overlay.enabled = False
        self.prefs.sonar_enabled = False
        if self.prefs.overlay_layers_release != "atlas-v070":
            self.prefs.overlay.layers = "atlas"
            self.prefs.overlay_layers_release = "atlas-v070"
        self.dataset, warning = recover_model(directory / "dataset.json", Dataset, load_model(PACKAGE / "data/dataset.json", Dataset))
        if warning:
            self.messages.append(warning)
        cache = directory / "events-cache.json"
        self.feed, warning = recover_model(cache, EventFeed, load_model(PACKAGE / "data/events.json", EventFeed))
        if warning:
            self.messages.append(warning)
        self.provider_status = "Cache local" if cache.exists() else "JSON local • offline"
        self.upgrade_bundled_content()
        self.upgrade_bundled_cube_sites()
        self.alerts = AlertEngine(directory / "alerts.json")
        self.normalize_map()
        if self.prefs.map_defaults_release != "altgard-v021":
            if any(m.id == "altgard" for m in self.dataset.maps):
                self.prefs.map_id = "altgard"
                self.prefs.catalog_map_id = "altgard"
                self.prefs.overlay.map_id = "altgard"
            self.prefs.map_defaults_release = "altgard-v021"

    def upgrade_bundled_content(self):
        """Replace only exact old bundled seeds; retain all custom imports and preferences."""
        previous_release = self.prefs.content_release
        fingerprints = json.loads((PACKAGE / "data/legacy-fingerprints.json").read_text(encoding="utf-8"))
        for attribute, model, filename, user_filename in [
            ("dataset", Dataset, "dataset.json", "dataset.json"),
            ("feed", EventFeed, "events.json", "events-cache.json"),
        ]:
            current = getattr(self, attribute)
            normalized = json.dumps(current.model_dump(mode="json"), sort_keys=True, ensure_ascii=True).encode()
            known = fingerprints[attribute]
            known = [known] if isinstance(known, str) else known
            if previous_release != "sa-live-overlay-v030" and hashlib.sha256(normalized).hexdigest() in known:
                path = self.directory / user_filename
                if path.exists():
                    old_version = "v010" if current.demo else ("v020" if getattr(current,"release","")=="latam-2026-10-11" else "v021")
                    backup = path.with_name(path.stem + f".{old_version}-backup.json")
                    if not backup.exists():
                        shutil.copy2(path, backup)
                replacement = load_model(PACKAGE / "data" / filename, model)
                atomic_json(path, replacement)
                setattr(self, attribute, replacement)
                self.messages.append("Base original atualizada; cópia anterior preservada.")
        if not previous_release:
            if self.prefs.timezone == "local":
                self.prefs.timezone = "America/Sao_Paulo"
        self.prefs.content_release = "sa-live-overlay-v030"

    def normalize_map(self):
        ids = {m.id for m in self.dataset.maps}
        default = "altgard" if "altgard" in ids else self.dataset.maps[0].id
        if self.prefs.map_id not in ids:
            self.prefs.map_id = default
        if self.prefs.catalog_map_id and self.prefs.catalog_map_id not in ids:
            self.prefs.catalog_map_id = default
        if self.prefs.overlay.map_id not in ids:
            self.prefs.overlay.map_id = self.prefs.map_id

    def upgrade_bundled_cube_sites(self):
        from app.core.corrections import upgrade_cube_sites
        provenance=json.loads((PACKAGE/'data/cube-sites-provenance.json').read_text(encoding='utf-8'))
        history=json.loads((PACKAGE/'data/coordinate-corrections.json').read_text(encoding='utf-8'))
        bundled=load_model(PACKAGE/'data/dataset.json',Dataset)
        upgraded,changes=upgrade_cube_sites(self.dataset,bundled,provenance,history)
        if changes:
            path=self.directory/'dataset.json'
            if path.exists():
                backup=path.with_name('dataset.v042-backup.json')
                if not backup.exists():
                    shutil.copy2(path,backup)
            atomic_json(path,upgraded)
            self.dataset=upgraded
            self.messages.append('Posições possíveis de cubos incorporadas; visitas antigas preservadas em camada separada. Ajuste aproximado de Basfelt retirado.')
        if self.prefs.cube_data_release != 'cube-sites-v050' and any(p.resource_id=='cube-spawns' for p in self.dataset.cubes):
            self.prefs.disabled_resources.add('cubes')
            self.prefs.cube_data_release='cube-sites-v050'
            atomic_json(self.directory/'preferences.json',self.prefs)

    def save(self):
        try:
            atomic_json(self.directory / "preferences.json", self.prefs)
        except OSError:
            logging.getLogger(__name__).exception("Falha ao salvar preferências")
            self.error.emit("Não foi possível salvar suas preferências. Verifique espaço e permissões.")
        self.changed.emit()

    def import_dataset(self, path: Path):
        dataset = load_model(path, Dataset)
        # Resolve relative raster paths against the imported JSON, then validate existence.
        for map_definition in dataset.maps:
            image = Path(map_definition.image)
            if not image.is_absolute() and (path.parent / image).is_file():
                map_definition.image = str((path.parent / image).resolve())
            if not resolve_map_image(map_definition.image).is_file():
                raise ValueError(f"Imagem não encontrada: {map_definition.image}")
            if Path(map_definition.image).is_absolute():
                from PySide6.QtGui import QImageReader
                original = Path(map_definition.image)
                if original.stat().st_size > 40_000_000:
                    raise ValueError("Imagem excede 40 MB")
                reader = QImageReader(str(original))
                size = reader.size()
                if not reader.canRead() or not size.isValid() or size.width() > 16000 or size.height() > 16000:
                    raise ValueError("Mapa raster inválido ou maior que 16000 pixels")
                digest = hashlib.sha256(original.read_bytes()).hexdigest()
                destination = self.directory / "maps" / (digest + original.suffix.lower())
                destination.parent.mkdir(exist_ok=True)
                if not destination.exists():
                    shutil.copyfile(original, destination)
                map_definition.image = str(destination)
        atomic_json(self.directory / "dataset.json", dataset)
        self.dataset = dataset
        self.prefs.overlay.enabled = False
        self.normalize_map()
        self.save()

    def import_events(self, path: Path):
        feed = load_model(path, EventFeed)
        self.accept_feed(feed, "JSON importado • cache local")

    def accept_feed(self, feed: EventFeed, status: str):
        atomic_json(self.directory / "events-cache.json", feed)
        self.feed = feed
        self.provider_status = status
        self.events_changed.emit()

    def select_agenda_profile(self, profile_id):
        profiles = json.loads((PACKAGE/"data/schedule-profiles.json").read_text(encoding="utf-8"))
        profile = next((p for p in profiles if p["id"]==profile_id),None)
        if not profile:
            raise ValueError("Perfil de agenda desconhecido")
        feed = load_model(PACKAGE/"data/profiles"/profile["file"],EventFeed)
        self.prefs.agenda_profile = profile_id
        self.accept_feed(feed,profile["name"]+" • offline")
        self.save()
