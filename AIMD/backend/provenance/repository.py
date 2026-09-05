import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from typing import Any


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "results" / "provenance.sqlite3"


def sanitize_source_url(source_url: str | None) -> str | None:
    if not source_url:
        return None

    try:
        parsed = urlsplit(source_url)
    except ValueError:
        return None

    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        return None

    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


class ProvenanceRepository:
    def __init__(self, database_path: str | Path | None = None):
        self.database_path = Path(database_path or DEFAULT_DATABASE_PATH)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS media_identity (
                    media_id TEXT PRIMARY KEY,
                    sha256 TEXT,
                    phash TEXT,
                    source_url TEXT,
                    platform TEXT,
                    first_seen_at TEXT NOT NULL,
                    metadata_summary TEXT NOT NULL
                )
                """
            )

    def record_media(
        self,
        media_id: str,
        sha256: str | None,
        phash: str | None,
        metadata_summary: dict[str, Any] | None = None,
        source_url: str | None = None,
        platform: str | None = None,
        first_seen_at: str | None = None,
    ) -> dict[str, Any]:
        observed_at = first_seen_at or datetime.now(timezone.utc).isoformat()
        safe_source_url = sanitize_source_url(source_url)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO media_identity
                    (media_id, sha256, phash, source_url, platform, first_seen_at, metadata_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(media_id) DO UPDATE SET
                    sha256 = excluded.sha256,
                    phash = excluded.phash,
                    source_url = excluded.source_url,
                    platform = excluded.platform,
                    metadata_summary = excluded.metadata_summary
                """ ,
                (
                    media_id,
                    sha256,
                    phash,
                    safe_source_url,
                    platform,
                    observed_at,
                    json.dumps(metadata_summary or {}, sort_keys=True),
                ),
            )

        return {
            "media_id": media_id,
            "sha256": sha256,
            "phash": phash,
            "source_url": safe_source_url,
            "platform": platform,
            "first_seen_at": observed_at,
            "metadata_summary": metadata_summary or {},
        }

    @staticmethod
    def _row_to_dict(row: sqlite3.Row, match_type: str, match_strength: str) -> dict[str, Any]:
        return {
            "media_id": row["media_id"],
            "sha256": row["sha256"],
            "phash": row["phash"],
            "source_url": sanitize_source_url(row["source_url"]),
            "platform": row["platform"],
            "first_seen_at": row["first_seen_at"],
            "metadata_summary": json.loads(row["metadata_summary"] or "{}"),
            "match_type": match_type,
            "match_strength": match_strength,
        }

    def find_exact(self, sha256: str | None, exclude_media_id: str | None = None) -> list[dict[str, Any]]:
        if not sha256:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM media_identity WHERE sha256 = ? AND media_id != ? ORDER BY first_seen_at",
                (sha256, exclude_media_id or ""),
            ).fetchall()
        return [self._row_to_dict(row, "EXACT", "STRONG") for row in rows]

    def all_with_phash(self, exclude_media_id: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM media_identity WHERE phash IS NOT NULL AND media_id != ? ORDER BY first_seen_at",
                (exclude_media_id or "",),
            ).fetchall()
        return [self._row_to_dict(row, "PERCEPTUAL", "BASELINE") for row in rows]