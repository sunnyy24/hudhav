import math
from numbers import Real
from typing import Any, Mapping


CONFIDENCE_NOTE = "Baseline ensemble confidence; not a calibrated probability."


def _is_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


def _unavailable(name: str, reason: str, technical_details: Mapping[str, Any] | None = None) -> dict:
    return {
        "name": name,
        "status": "unavailable",
        "strength": "insufficient",
        "summary": reason,
        "technical_details": dict(technical_details or {}),
    }


def _contextual_signal(name: str, result: Any) -> dict:
    if not isinstance(result, Mapping):
        return _unavailable(name, "This signal did not return a structured result.")

    if str(result.get("status", "available")).lower() == "unavailable":
        return _unavailable(name, str(result.get("reason", "Signal unavailable.")), result)

    if result.get("error"):
        return _unavailable(name, "The detector reported an error for this signal.", result)

    return {
        "name": name,
        "status": "available",
        "strength": "unknown",
        "summary": "Signal is available as contextual forensic evidence; no calibrated anomaly threshold is currently available.",
        "technical_details": dict(result),
    }


def _ml_signal(result: Any) -> tuple[dict, str | None, float | None, str | None]:
    if not isinstance(result, Mapping):
        return _unavailable("ML Detection", "The ML detector did not return a structured result."), None, None, "unavailable"

    if str(result.get("status", "available")).lower() == "unavailable":
        return _unavailable("ML Detection", str(result.get("reason", "ML detector unavailable.")), result), None, None, "unavailable"

    ai_probability = result.get("ai_probability")
    human_probability = result.get("human_probability")
    if not (_is_number(ai_probability) and _is_number(human_probability)):
        return _unavailable("ML Detection", "The ML detector did not provide usable probabilities.", result), None, None, "unavailable"

    ai_probability = float(ai_probability)
    human_probability = float(human_probability)
    margin = abs(ai_probability - human_probability)
    prediction = str(result.get("prediction", "")).upper()

    if ai_probability >= 0.65 and human_probability >= 0.65:
        direction = "conflict"
        summary = "The ML probabilities are internally conflicting and require further review."
        strength = "moderate"
    elif ai_probability >= 0.75 and ai_probability - human_probability >= 0.20:
        direction = "ai"
        summary = "The ML detector assigns a high AI-generation probability."
        strength = "strong" if ai_probability >= 0.85 else "moderate"
    elif human_probability >= 0.75 and human_probability - ai_probability >= 0.20:
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
    evidence = {
        "name": "ML Detection",
        "status": "available",
        "strength": strength,
        "summary": summary,
        "technical_details": technical_details,
    }

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
    signals = [ml_evidence]

    metadata_evidence = _contextual_signal("Metadata", metadata)
    signals.append(metadata_evidence)

    forensic_features = forensic_features or {}
    signals.extend([
        _contextual_signal("Frequency Analysis", forensic_features.get("frequency")),
        _contextual_signal("Compression Analysis", forensic_features.get("compression")),
        _contextual_signal("Noise Analysis", forensic_features.get("noise")),
    ])

    signals.append(_contextual_signal("File Fingerprint", fingerprints))
    signals.append(_unavailable("Provenance", "No verified provenance source is connected to this analysis."))
    if provenance is not None:
        signals[-1] = _contextual_signal("Provenance", provenance)

    available_context = sum(signal["status"] == "available" for signal in signals[1:])
    reasoning = []

    if direction == "ai":
        verdict = "LIKELY AI-GENERATED"
        evidence_strength = ml_evidence["strength"].upper()
        reasoning.append("The ML detector assigns a high AI-generation probability.")
    elif direction == "human":
        verdict = "LIKELY AUTHENTIC"
        evidence_strength = ml_evidence["strength"].upper()
        reasoning.append("The ML detector assigns a higher probability to human-created media.")
    else:
        verdict = "INCONCLUSIVE"
        evidence_strength = "INSUFFICIENT" if ml_status == "unavailable" else "WEAK"
        if direction == "conflict":
            reasoning.append("The available ML evidence is conflicting or too close to support a directional verdict.")
        else:
            reasoning.append("The available evidence is insufficient to support a directional verdict.")

    if available_context:
        reasoning.append("Forensic measurements are available as contextual evidence, but no calibrated anomaly thresholds are configured.")

    if metadata_evidence["status"] != "available":
        reasoning.append("The available metadata does not establish a verified origin.")

    if ml_status == "unavailable":
        reasoning.append("The ML detector is unavailable, so the ensemble cannot make an AI-versus-human assessment.")

    return {
        "verdict": verdict,
        "confidence": round(ml_confidence if ml_confidence is not None and direction in {"ai", "human"} else (0.25 if direction == "conflict" else 0.10), 6),
        "evidence_strength": evidence_strength,
        "confidence_note": CONFIDENCE_NOTE,
        "signals": signals,
        "reasoning": reasoning,
    }