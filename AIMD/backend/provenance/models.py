from typing import Any, TypedDict


class ProvenanceFinding(TypedDict):
    type: str
    status: str
    confidence: float | None
    summary: str
    technical_details: dict[str, Any]


def finding(
    finding_type: str,
    status: str,
    summary: str,
    technical_details: dict[str, Any] | None = None,
    confidence: float | None = None,
) -> ProvenanceFinding:
    return {
        "type": finding_type,
        "status": status,
        "confidence": confidence,
        "summary": summary,
        "technical_details": technical_details or {},
    }