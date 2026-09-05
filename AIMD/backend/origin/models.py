from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ProviderStatus = Literal["VERIFIED", "UNKNOWN", "ERROR", "UNAVAILABLE"]
MatchType = Literal["EXACT", "PARTIAL", "PERCEPTUAL", "UNKNOWN"]
MatchStrength = Literal["VERIFIED", "INFERRED", "UNKNOWN"]


@dataclass(frozen=True)
class OriginMatch:
    source_url: str | None = None
    platform: str | None = None
    title: str | None = None
    first_seen: str | None = None
    match_type: MatchType = "UNKNOWN"
    match_strength: MatchStrength = "UNKNOWN"
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderResult:
    provider: str
    status: ProviderStatus
    searched_at: str
    matches: list[OriginMatch] = field(default_factory=list)
    error: str | None = None
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status,
            "searched_at": self.searched_at,
            "matches": [match.to_dict() for match in self.matches],
            "error": self.error,
            "cached": self.cached,
        }