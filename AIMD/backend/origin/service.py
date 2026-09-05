import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from origin.models import OriginMatch, ProviderResult
from origin.policy import is_external_search_enabled, is_google_provider_configured
from origin.providers.base import OriginProvider
from origin.providers.google_web_detection import GoogleWebDetectionProvider
from provenance.repository import DEFAULT_DATABASE_PATH, sanitize_source_url


CACHE_TTL = timedelta(minutes=10)


class OriginSearchRepository:
    def __init__(self, database_path: str | Path | None = None):
        self.database_path = Path(database_path or DEFAULT_DATABASE_PATH)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS origin_searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL,
                    searched_at TEXT NOT NULL,
                    error TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS origin_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_id INTEGER NOT NULL,
                    source_url TEXT,
                    platform TEXT,
                    title TEXT,
                    first_seen TEXT,
                    match_type TEXT NOT NULL,
                    match_strength TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    FOREIGN KEY(search_id) REFERENCES origin_searches(id)
                )
                """
            )

    def cached_result(self, file_id: str, provider: str) -> ProviderResult | None:
        with self._connect() as connection:
            search = connection.execute(
                "SELECT * FROM origin_searches WHERE file_id = ? AND provider = ? AND status IN ('VERIFIED', 'UNKNOWN') ORDER BY id DESC LIMIT 1",
                (file_id, provider),
            ).fetchone()
            if search is None:
                return None

            try:
                searched_at = datetime.fromisoformat(search["searched_at"])
            except ValueError:
                return None
            if datetime.now(timezone.utc) - searched_at > CACHE_TTL:
                return None

            rows = connection.execute(
                "SELECT * FROM origin_matches WHERE search_id = ? ORDER BY id",
                (search["id"],),
            ).fetchall()

        matches = [
            OriginMatch(
                source_url=sanitize_source_url(row["source_url"]),
                platform=row["platform"],
                title=row["title"],
                first_seen=row["first_seen"],
                match_type=row["match_type"],
                match_strength=row["match_strength"],
                evidence=json.loads(row["evidence_json"]),
            )
            for row in rows
        ]
        return ProviderResult(search["provider"], search["status"], search["searched_at"], matches, search["error"], cached=True)

    def save(self, file_id: str, result: ProviderResult) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO origin_searches (file_id, provider, status, searched_at, error) VALUES (?, ?, ?, ?, ?)",
                (file_id, result.provider, result.status, result.searched_at, result.error),
            )
            search_id = cursor.lastrowid
            for match in result.matches:
                connection.execute(
                    "INSERT INTO origin_matches (search_id, source_url, platform, title, first_seen, match_type, match_strength, evidence_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        search_id,
                        sanitize_source_url(match.source_url),
                        match.platform,
                        match.title,
                        match.first_seen,
                        match.match_type,
                        match.match_strength,
                        json.dumps(match.evidence, sort_keys=True),
                    ),
                )


def unavailable_result(provider: str, error: str) -> ProviderResult:
    return ProviderResult(
        provider=provider,
        status="UNAVAILABLE",
        searched_at=datetime.now(timezone.utc).isoformat(),
        error=error,
    )


async def search_external_origin(
    file_id: str,
    image_path: str,
    filename: str | None = None,
    provider: OriginProvider | None = None,
    repository: OriginSearchRepository | None = None,
) -> ProviderResult:
    selected_provider = provider or GoogleWebDetectionProvider()
    search_repository = repository or OriginSearchRepository()

    cached = search_repository.cached_result(file_id, selected_provider.name)
    if cached is not None:
        return cached

    if not is_external_search_enabled():
        return unavailable_result(selected_provider.name, "External origin discovery is disabled.")

    if selected_provider.name == "google_web_detection" and not is_google_provider_configured():
        return unavailable_result(selected_provider.name, "Google Web Detection is not configured.")

    try:
        image = Path(image_path).read_bytes()
    except OSError:
        return unavailable_result(selected_provider.name, "The uploaded image could not be read.")

    result = await selected_provider.search(image, filename=filename)
    if result.error and any(term in result.error.lower() for term in ("api_key", "api-key", "token", "secret")):
        result.error = "Provider request failed."
    result.matches = [
        OriginMatch(
            source_url=sanitize_source_url(match.source_url),
            platform=match.platform,
            title=match.title,
            first_seen=match.first_seen,
            match_type=match.match_type,
            match_strength=match.match_strength,
            evidence=match.evidence,
        )
        for match in result.matches
    ]
    if result.status in {"VERIFIED", "UNKNOWN"}:
        search_repository.save(file_id, result)
    return result