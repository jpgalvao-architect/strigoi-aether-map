# SPDX-License-Identifier: GPL-3.0-only
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(directory: Path):
    logs = directory / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(logs / "strigoi.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
