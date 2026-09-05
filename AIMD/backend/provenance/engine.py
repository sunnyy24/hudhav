from pathlib import Path
from typing import Any

from forensic.hashing import phash_image, sha256_file
from provenance.c2pa import inspect_content_credentials
from provenance.models import finding
from provenance.repository import ProvenanceRepository
from provenance.similarity import configured_phash_threshold, phash_hamming_distance


def _verified_or_unknown(value: Any) -> dict[str, Any]:
    if value is None or value == "":
        return {"status": "UNKNOWN", "value": None}
    return {"status": "VERIFIED", "value": value}


def metadata_origin(metadata: dict[str, Any] | None) -> dict[str, Any]:
    metadata = metadata or {}
    exif = metadata.get("exif") or {}
    make = exif.get("271")
    model = exif.get("272")
    capture_device = " ".join(str(value) for value in (make, model) if value) or None

    return {
        "capture_device": _verified_or_unknown(capture_device),
        "camera_make": _verified_or_unknown(make),
        "camera_model": _verified_or_unknown(model),
        "capture_timestamp": _verified_or_unknown(exif.get("306")),
        "editing_software": _verified_or_unknown(exif.get("305")),
        "gps_availability": _verified_or_unknown("present" if exif.get("34853") else None),
        "exif_present": _verified_or_unknown(True if metadata.get("exif_present") else None),
    }


def platform_processing_evidence(
    file_path: str,
    metadata: dict[str, Any] | None,
    compression: dict[str, Any] | None,
) -> dict[str, Any]:
    suffix = Path(file_path).suffix.lower()
    metadata = metadata or {}
    compression = compression or {}
    reasoning = []

    if suffix in {".jpg", ".jpeg"} and compression.get("vertical_block_boundary_mean") is not None:
        reasoning.append("JPEG block-boundary measurements are available and are consistent with image compression or re-encoding.")
        if not metadata.get("exif_present"):
            reasoning.append("No EXIF metadata is present; stripping cannot be distinguished from original absence from this signal alone.")
        return {
            "status": "INFERRED",
            "platform_processing": "POSSIBLE",
            "reasoning": reasoning,
            "technical_details": {"extension": suffix, "compression": compression},
        }

    return {
        "status": "UNKNOWN",
        "platform_processing": "UNKNOWN",
        "reasoning": ["No platform-specific processing evidence was established from the available local signals."],
        "technical_details": {"extension": suffix, "compression": compression},
    }


def _origin_record(matches: list[dict[str, Any]]) -> dict[str, Any]:
    if not matches:
        return {
            "source_url": None,
            "platform": None,
            "first_seen_at": None,
            "match_type": "NONE",
            "match_strength": "UNKNOWN",
            "status": "UNKNOWN",
        }

    match = matches[0]
    return {
        "source_url": match.get("source_url"),
        "platform": match.get("platform"),
        "first_seen_at": match.get("first_seen_at"),
        "match_type": match["match_type"],
        "match_strength": match["match_strength"],
        "status": "VERIFIED" if match.get("source_url") else "UNKNOWN",
    }


def trace_provenance(
    file_path: str,
    fingerprints: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    compression: dict[str, Any] | None = None,
    media_id: str | None = None,
    repository: ProvenanceRepository | None = None,
    content_credentials_reader=None,
) -> dict[str, Any]:
    fingerprints = fingerprints or {}
    sha256 = fingerprints.get("sha256")
    phash = fingerprints.get("phash")
    if not isinstance(sha256, str):
        try:
            sha256 = sha256_file(file_path)
        except Exception:
            sha256 = None
    if not isinstance(phash, str):
        try:
            phash = phash_image(file_path)
        except Exception:
            phash = None

    current_media_id = media_id or Path(file_path).stem
    provenance_repository = repository or ProvenanceRepository()
    exact_matches = provenance_repository.find_exact(sha256, exclude_media_id=current_media_id)
    perceptual_matches = []
    threshold = configured_phash_threshold()
    if phash:
        for candidate in provenance_repository.all_with_phash(exclude_media_id=current_media_id):
            distance = phash_hamming_distance(phash, candidate.get("phash"))
            if distance is not None and distance <= threshold:
                candidate["distance"] = distance
                perceptual_matches.append(candidate)

    exact_media_ids = {candidate["media_id"] for candidate in exact_matches}
    matches = exact_matches + [
        candidate
        for candidate in perceptual_matches
        if candidate["media_id"] not in exact_media_ids
    ]
    recorded = provenance_repository.record_media(
        media_id=current_media_id,
        sha256=sha256,
        phash=phash,
        metadata_summary={
            "format": (metadata or {}).get("format"),
            "width": (metadata or {}).get("width"),
            "height": (metadata or {}).get("height"),
            "exif_present": (metadata or {}).get("exif_present"),
        },
    )

    credentials = inspect_content_credentials(file_path, reader=content_credentials_reader)
    processing = platform_processing_evidence(file_path, metadata, compression)
    identity = {
        "sha256": sha256,
        "phash": phash,
        "identity_status": "VERIFIED" if sha256 else "UNKNOWN",
    }
    metadata_origin_result = metadata_origin(metadata)
    findings = [
        finding("MEDIA_IDENTITY", "VERIFIED" if sha256 else "UNKNOWN", "SHA-256 identifies this exact local artifact." if sha256 else "An exact artifact identity could not be established.", identity),
        finding("METADATA_ORIGIN", "VERIFIED" if any(field["status"] == "VERIFIED" for field in metadata_origin_result.values()) else "UNKNOWN", "Available metadata was mapped without treating absence as proof of origin.", metadata_origin_result),
        finding("CONTENT_CREDENTIALS", credentials["status"], "Content Credentials were detected." if credentials.get("present") else credentials.get("reason", "Content Credentials were not detected."), credentials),
        finding("PLATFORM_PROCESSING", processing["status"], "Possible processing was inferred from local image characteristics." if processing["status"] == "INFERRED" else "Platform processing was not established.", processing),
        finding("LOCAL_MATCHES", "VERIFIED" if matches else "UNKNOWN", "A prior local identity match was found." if matches else "No prior local provenance match was found.", {"count": len(matches), "phash_threshold": threshold}),
    ]

    return {
        "identity": identity,
        "metadata_origin": metadata_origin_result,
        "content_credentials": credentials,
        "platform_processing": processing,
        "matches": matches,
        "origin": _origin_record(matches),
        "timeline": [
            {
                "event": "AIMD local artifact observed",
                "date": recorded["first_seen_at"],
                "status": "VERIFIED",
                "source": "AIMD local intake",
            },
        ],
        "findings": findings,
        "external_search": {
            "performed": False,
            "status": "UNKNOWN",
            "reason": "External platform search not performed.",
        },
    }