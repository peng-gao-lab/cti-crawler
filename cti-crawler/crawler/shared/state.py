import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from .article_ids import is_numbered_name
from .reports import merge_metadata


class StateStore:
    def __init__(self, path: Path, track_failures: bool = False):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self.run_id = datetime.now(timezone.utc).isoformat()
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS completed (
                source TEXT NOT NULL,
                url TEXT NOT NULL,
                filename TEXT NOT NULL,
                completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source, url)
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                source TEXT NOT NULL,
                url TEXT NOT NULL,
                filename TEXT NOT NULL,
                metadata TEXT NOT NULL,
                PRIMARY KEY (source, url),
                UNIQUE (source, filename)
            )
            """
        )
        # Import old CTI completion records once; existing APT reservations win.
        self._connection.execute(
            """INSERT OR IGNORE INTO reports (source, url, filename, metadata)
               SELECT source, url, filename, '{}' FROM completed"""
        )
        if track_failures:
            self._connection.execute(
                "CREATE TABLE IF NOT EXISTS failures (id INTEGER PRIMARY KEY, record TEXT NOT NULL)"
            )
        self._connection.commit()

    def is_completed(self, source: str, url: str) -> bool:
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM completed WHERE source = ? AND url = ?",
                (source, url),
            ).fetchone()
        return row is not None

    def mark_completed(self, source: str, url: str, filename: str, metadata: dict | None = None) -> None:
        with self._lock:
            if metadata is not None:
                row = self._connection.execute(
                    "SELECT metadata FROM reports WHERE source = ? AND url = ?",
                    (source, url),
                ).fetchone()
                merged = merge_metadata(json.loads(row[0]), metadata)
                self._connection.execute(
                    "UPDATE reports SET metadata = ? WHERE source = ? AND url = ?",
                    (json.dumps(merged, ensure_ascii=False), source, url),
                )
            self._connection.execute(
                """INSERT INTO completed (source, url, filename) VALUES (?, ?, ?)
                   ON CONFLICT(source, url) DO UPDATE SET filename = excluded.filename""",
                (source, url, filename),
            )
            self._connection.commit()

    def get_report(self, source: str, url: str) -> dict | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT filename, metadata FROM reports WHERE source = ? AND url = ?",
                (source, url),
            ).fetchone()
        return {"filename": row[0], "metadata": json.loads(row[1])} if row else None

    def prepare_report(self, source: str, url: str, preferred_name: str, metadata: dict, storage) -> str:
        """Persist file ownership before writing, without recording completion."""
        with self._lock:
            row = self._connection.execute(
                "SELECT filename, metadata FROM reports WHERE source = ? AND url = ?",
                (source, url),
            ).fetchone()
            preferred = Path(preferred_name)
            if row and Path(row[0]).suffix == preferred.suffix:
                filename = row[0]
            elif is_numbered_name(preferred_name):
                # A numbered name belongs to exactly one identity; a clash is a registry/state
                # inconsistency that must surface, never be hidden behind a __2 suffix.
                owner = self._connection.execute(
                    "SELECT url FROM reports WHERE source = ? AND filename = ?", (source, preferred_name),
                ).fetchone()
                if (owner and owner[0] != url) or (not owner and storage.exists(preferred_name)):
                    raise ValueError(f"Article number file {preferred_name} already belongs to another identity in {source}")
                filename = preferred_name
            else:
                filename = preferred_name
                suffix = 2
                while self._connection.execute(
                    "SELECT 1 FROM reports WHERE source = ? AND filename = ?",
                    (source, filename),
                ).fetchone() or storage.exists(filename):
                    filename = f"{preferred.stem}__{suffix}{preferred.suffix}"
                    suffix += 1
            merged = merge_metadata(json.loads(row[1]) if row else {}, metadata)
            self._connection.execute(
                """INSERT INTO reports (source, url, filename, metadata) VALUES (?, ?, ?, ?)
                   ON CONFLICT(source, url) DO UPDATE SET
                       filename = excluded.filename, metadata = excluded.metadata""",
                (source, url, filename, json.dumps(merged, ensure_ascii=False)),
            )
            self._connection.commit()
        return filename

    def unmark_completed(self, source: str, url: str) -> None:
        with self._lock:
            self._connection.execute("DELETE FROM completed WHERE source = ? AND url = ?", (source, url))
            self._connection.commit()

    def completed_reports(self) -> list[tuple]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT c.source, c.url, c.filename, r.metadata
                   FROM completed c JOIN reports r
                   ON c.source = r.source AND c.url = r.url AND c.filename = r.filename
                   ORDER BY c.source, c.url"""
            ).fetchall()
        return [(source, url, filename, json.loads(metadata)) for source, url, filename, metadata in rows]

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def record_failure(self, record: dict) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT INTO failures (record) VALUES (?)",
                (json.dumps({**record, "run_id": self.run_id}, ensure_ascii=False),),
            )
            self._connection.commit()

    def failure_records(self) -> list[dict]:
        with self._lock:
            rows = self._connection.execute("SELECT record FROM failures ORDER BY id").fetchall()
        return [json.loads(row[0]) for row in rows]
