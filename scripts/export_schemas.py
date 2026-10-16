# SPDX-License-Identifier: GPL-3.0-only
"""Run from project root: python scripts/export_schemas.py."""
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from app.core.models import Dataset, EventFeed, Preferences
from app.modules.overlay.detector import Calibration
from app.modules.overlay.selection import CaptureArea
from app.modules.pets.models import PetCatalogue, PetCollection, PetSites
from app.modules.routine.models import RoutineCollection

destination = root / "schemas"
destination.mkdir(exist_ok=True)
for name, model in [("dataset", Dataset), ("event-feed", EventFeed), ("preferences", Preferences), ("calibration", Calibration), ("capture-area", CaptureArea), ("pets", PetCatalogue), ("pet-collection", PetCollection), ("pet-sites", PetSites), ("routine",RoutineCollection)]:
    (destination / f"{name}.schema.json").write_text(json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Schemas exported to {destination}")
