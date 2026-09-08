import math
from numbers import Real
from typing import Any, Mapping


CONFIDENCE_NOTE = "Baseline ensemble confidence; not a calibrated probability."
CONTEXT_NOTE = (
    "Frequency, compression, noise, and image statistics are shown as contextual "
    "forensic evidence and are not converted into unsupported anomaly scores."
)

LIMITATIONS = [
    "AI detectors can produce false positives and false negatives.",
    "Performance varies across image generators, editing tools, formats and image content.",
    "Compression and social-media re-encoding can alter forensic evidence.",
    "Missing metadata is not proof of AI generation.",
    "Missing Content Credentials is not proof of AI generation.",
    "Ensemble confidence is a baseline assessment, not a calibrated probability.",
    "Frequency, compression, and noise values do not currently have validated anomaly thresholds.",
    "Current implementation analyzes images.",
    "Manipulated-region localization is not currently implemented.",
    "Human review may be required for consequential decisions.",
]


def _is_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


def _signal(
    name: str,
    status: str,
    summary: str,
    *,
    strength: str = "unknown",
    technical_details: Mapping[str, Any] | None = None,
) -> dict:
    return {
        "name": name,
        "status": status.upper(),
        "strength": strength,
        "summary": summary,
        "technical_details": dict(technical_details or {}),
    }


def _unavailable(name: str, reason: str, technical_details: Mapping[str, Any] | None = None) -> dict:
    return _signal(name, "UNAVAILABLE", reason, strength="insufficient", technical_details=technical_details)


def _error(name: str, reason: str, technical_details: Mapping[str, Any] | None = None) -> dict:
    return _signal(name, "ERROR", reason, strength="insufficient", technical_details=technical_details)


def _normalize_status(result: Mapping[str, Any], default: str = "INFERRED") -> str:
    raw = str(result.get("status", default)).upper()
    aliases = {
        "AVAILABLE": default,
        "OK": default,
        "SUCCESS": default,
    }
    return aliases.get(raw, raw if raw in {"VERIFIED", "INFERRED", "UNKNOWN", "UNAVAILABLE", "ERROR"} else default)


def _contextual_signal(name: str, result: Any, *, default_status: str = "INFERRED") -> dict:
    if result is None:
        return _unavailable(name, "This signal was not produced for this analysis.")
    if not isinstance(result, Mapping):
        return _unavailable(name, "This signal did not return a structured result.")

    status = _normalize_status(result, default_status)
    if status == "UNAVAILABLE":
        return _unavailable(name, str(result.get("reason", "Signal unavailable.")), result)
    if status == "ERROR" or result.get("error"):
        return _error(name, str(result.get("reason") or result.get("error") or "The detector reported an error for this signal."), result)

    return _signal(
        name,
        status,
        "Signal is available as contextual forensic evidence; no calibrated anomaly threshold is currently available.",
        strength="unknown",
        technical_details=result,
    )


def _identity_signal(fingerprints: Any) -> dict:
    if not isinstance(fingerprints, Mapping):
        return _unavailable("File Identity", "File fingerprints were not produced.")

    sha256 = fingerprints.get("sha256")
    phash = fingerprints.get("phash")
    sha256_value = sha256 if isinstance(sha256, str) else None
    phash_value = phash if isinstance(phash, str) else None
    if not sha256_value and not phash_value:
        return _unavailable("File Identity", "SHA-256 and pHash were not produced.", fingerprints)

    return _signal(
        "File Identity",
        "VERIFIED" if sha256_value else "INFERRED",
        "SHA-256 identifies exact byte-for-byte equality. pHash supports perceptual comparison and does not prove common origin.",
        strength="unknown",
        technical_details={"sha256": sha256_value, "phash": phash_value},
    )


def _credentials_signal(credentials: Any) -> dict:
    if not isinstance(credentials, Mapping):
        return _unavailable(
            "Content Credentials",
            "Content Credentials inspection unavailable.",
        )
    status = str(credentials.get("status", "UNKNOWN")).upper()
    if status == "UNAVAILABLE" or (
        not credentials.get("present")
        and "unavailable" in str(credentials.get("reason", "")).lower()
    ):
        return _unavailable(
            "Content Credentials",
            credentials.get("reason") or "Content Credentials inspection unavailable.",
            credentials,
        )
    if credentials.get("present"):
        return _signal(
            "Content Credentials",
            "VERIFIED",
            "Content Credentials were detected on this artifact.",
            strength="unknown",
            technical_details=credentials,
        )
    return _signal(
        "Content Credentials",
        "UNKNOWN",
        credentials.get("reason") or "No Content Credentials were detected. Absence is not proof of AI generation.",
        strength="unknown",
        technical_details=credentials,
    )


def _provenance_signal(provenance: Any) -> dict:
    if not isinstance(provenance, Mapping):
        return _unavailable("Local Provenance", "Local provenance was not connected to this analysis.")

    matches = provenance.get("matches") or []
    identity = provenance.get("identity") or {}
    if matches:
        summary = "A prior AIMD observation matched this artifact by SHA-256 or pHash. A pHash match does not prove common origin."
        status = "VERIFIED"
    elif identity.get("sha256"):
        summary = "Local provenance recorded this observation. No prior exact or perceptual match was found."
        status = "INFERRED"
    else:
        summary = "Local provenance could not establish an earlier AIMD observation."
        status = "UNKNOWN"

    return _signal(
        "Local Provenance",
        status,
        summary,
        strength="unknown",
        technical_details={
            "identity": identity,
            "match_count": len(matches),
            "origin": provenance.get("origin"),
        },
    )


def _ml_signal(result: Any) -> tuple[dict, str | None, float | None, str | None]:
    if not isinstance(result, Mapping):
        return _unavailable("ML Classification", "The ML detector did not return a structured result."), None, None, "unavailable"

    status = str(result.get("status", "available")).lower()
    if status == "unavailable":
        return _unavailable("ML Classification", str(result.get("reason", "ML detector unavailable.")), result), None, None, "unavailable"
    if status == "error":
        return _error("ML Classification", str(result.get("reason", "ML detector error.")), result), None, None, "unavailable"

    ai_probability = result.get("ai_probability")
    human_probability = result.get("human_probability")
    if not (_is_number(ai_probability) and _is_number(human_probability)):
        return _unavailable("ML Classification", "The ML detector did not provide usable probabilities.", result), None, None, "unavailable"

    ai_probability = float(ai_probability)
    human_probability = float(human_probability)
    margin = abs(ai_probability - human_probability)
    prediction = str(result.get("prediction", "")).upper()

    if ai_probability >= 0.65 and human_probability >= 0.65:
        direction = "conflict"
        summary = "The ML probabilities are internally conflicting and require further review."
        strength = "moderate"
    elif ai_probability >= 0.70 and ai_probability - human_probability >= 0.20:
        direction = "ai"
        summary = "The ML detector assigns a high AI-generation probability."
        strength = "strong" if ai_probability >= 0.85 else "moderate"
    elif human_probability >= 0.70 and human_probability - ai_probability >= 0.20:
        direction = "human"
        summary = "The ML detector assigns a higher probability to human-created media."
        strength = "strong" if human_probability >= 0.85 else "moderate"
    else:
        direction = None
        summary = "The ML probabilities are not separated enough to support a directional verdict."
        strength = "weak"

    technical_details = {
        "model": result.get("model"),
        "prediction": result.get("prediction"),
        "confidence": result.get("confidence"),
        "ai_probability": ai_probability,
        "human_probability": human_probability,
        "raw_scores": result.get("raw_scores", {}),
        "probability_margin": round(margin, 6),
    }
    evidence = _signal(
        "ML Classification",
        "INFERRED",
        summary,
        strength=strength,
        technical_details=technical_details,
    )

    if prediction not in {"AI-GENERATED", "HUMAN"} and direction is None:
        direction = "conflict"

    confidence = result.get("confidence")
    if not _is_number(confidence):
        confidence = max(ai_probability, human_probability)

    return evidence, direction, min(max(float(confidence), 0.0), 1.0), "available"


def assess_ensemble(
    *,
    ml_detection: Mapping[str, Any],
    metadata: Mapping[str, Any] | None,
    forensic_features: Mapping[str, Any] | None,
    fingerprints: Mapping[str, Any] | None = None,
    provenance: Mapping[str, Any] | None = None,
) -> dict:
    if not isinstance(ml_detection, Mapping):
        raise ValueError("ml_detection must be a mapping")
    if forensic_features is not None and not isinstance(forensic_features, Mapping):
        raise ValueError("forensic_features must be a mapping or None")

    ml_evidence, direction, ml_confidence, ml_status = _ml_signal(ml_detection)
    forensic_features = forensic_features or {}
    credentials = provenance.get("content_credentials") if isinstance(provenance, Mapping) else None

    signals = [
        ml_evidence,
        _contextual_signal("Metadata", metadata, default_status="INFERRED"),
        _identity_signal(fingerprints),
        _contextual_signal("Frequency Analysis", forensic_features.get("frequency")),
        _contextual_signal("Compression Analysis", forensic_features.get("compression")),
        _contextual_signal("Noise Analysis", forensic_features.get("noise")),
        _contextual_signal("Image Statistics", forensic_features.get("statistics")),
        _credentials_signal(credentials),
        _provenance_signal(provenance),
        _unavailable(
            "Online Origin Discovery",
            "External origin discovery is optional, consent-gated, and was not performed during local analysis.",
        ),
    ]

    metadata_evidence = signals[1]
    available_context = sum(signal["status"] in {"VERIFIED", "INFERRED"} for signal in signals[1:])
    reasoning = []

    if direction == "ai":
        verdict = "LIKELY AI-GENERATED"
        evidence_strength = ml_evidence["strength"].upper()
        verdict_explanation = "ML classification is strongly directional toward AI generation."
        reasoning.append(verdict_explanation)
    elif direction == "human":
        verdict = "LIKELY AUTHENTIC"
        evidence_strength = ml_evidence["strength"].upper()
        verdict_explanation = "ML classification is strongly directional toward human-created media."
        reasoning.append(verdict_explanation)
    else:
        verdict = "INCONCLUSIVE"
        evidence_strength = "INSUFFICIENT" if ml_status == "unavailable" else "WEAK"
        if direction == "conflict":
            verdict_explanation = "ML classification is conflicting or too close to support a directional verdict."
        elif ml_status == "unavailable":
            verdict_explanation = "The open-weight classifier was unavailable, so AIMD cannot support a directional verdict."
        else:
            verdict_explanation = "The available evidence is insufficient to support a directional verdict."
        reasoning.append(verdict_explanation)

    if available_context:
        reasoning.append(CONTEXT_NOTE)

    if metadata_evidence["status"] not in {"VERIFIED", "INFERRED"}:
        reasoning.append("The available metadata does not establish a verified origin. Missing metadata is not proof of AI generation.")
    else:
        reasoning.append("Available metadata is shown as provenance context. Missing fields are not treated as AI evidence.")

    if ml_status == "unavailable":
        reasoning.append("The ML detector is unavailable, so the ensemble cannot make an AI-versus-human assessment.")

    reasoning.append("POTENTIALLY AI-ALTERED is reserved for a future validated manipulation signal and is not inferred by this pipeline.")

    return {
        "verdict": verdict,
        "confidence": round(
            ml_confidence if ml_confidence is not None and direction in {"ai", "human"} else (0.25 if direction == "conflict" else 0.10),
            6,
        ),
        "evidence_strength": evidence_strength,
        "confidence_note": CONFIDENCE_NOTE,
        "verdict_explanation": verdict_explanation,
        "signals": signals,
        "reasoning": reasoning,
        "limitations": LIMITATIONS,
    }
