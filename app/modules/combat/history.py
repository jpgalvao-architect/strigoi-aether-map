# SPDX-License-Identifier: GPL-3.0-only
"""Transactional local summaries. No raw packets, credentials or uploads."""
import json
import sqlite3
from datetime import UTC, datetime


class CombatHistory:
    def __init__(self, path):
        self.path = path
        self.connection = sqlite3.connect(path)
        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if version > 1:
            self.connection.close()
            raise ValueError("Unsupported combat history version")
        with self.connection:
            self.connection.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, updated TEXT NOT NULL, summary TEXT NOT NULL)")
            self.connection.execute("PRAGMA user_version=1")

    def save(self, summary):
        if not summary["run_id"] or not summary["encounters"]:
            return
        with self.connection:
            self.connection.execute("INSERT INTO runs VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET updated=excluded.updated,summary=excluded.summary",
                (summary["run_id"], datetime.now(UTC).isoformat(), json.dumps(summary, ensure_ascii=False)))
            self.connection.execute("DELETE FROM runs WHERE id NOT IN (SELECT id FROM runs ORDER BY updated DESC LIMIT 200)")

    def list(self):
        rows = []
        for stamp, encoded in self.connection.execute("SELECT updated,summary FROM runs ORDER BY updated DESC LIMIT 200"):
            summary = json.loads(encoded)
            if summary.get("active"):
                summary["active"] = False
                summary["issues"] = sorted(set(summary.get("issues", [])) | {"unfinished_capture"})
                for attempt in summary.get("attempts", []):
                    if attempt.get("result") == "active":
                        attempt["result"] = "interrupted"
                        attempt["active"] = False
            rows.append((stamp, summary))
        return rows

    def delete(self, run_id):
        with self.connection:
            self.connection.execute("DELETE FROM runs WHERE id=?", (run_id,))

    def close(self):
        self.connection.close()
