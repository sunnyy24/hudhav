from pathlib import Path

from forensic.hashing import (
    sha256_file,
    phash_image,
)

from forensic.metadata import extract_metadata
from forensic.frequency import frequency_analysis
from forensic.compression import compression_analysis
from forensic.noise import noise_analysis
from forensic.ensemble import assess_ensemble
from provenance.engine import trace_provenance

from detectors.image_detector import get_detector


# Supported image formats
IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


def _run_signal(function, file_path: str, name: str) -> dict:
    try:
        return function(file_path)
    except Exception:
        return {
            "status": "unavailable",
            "reason": f"{name} analysis was unavailable.",
        }


def _run_ml_detector(file_path: str) -> dict:
    try:
        return get_detector().predict(file_path)
    except Exception:
        return {
            "status": "unavailable",
            "prediction": "INCONCLUSIVE",
            "confidence": 0.0,
            "ai_probability": None,
            "human_probability": None,
            "raw_scores": {},
            "reason": "ML detection was unavailable.",
        }


def analyze_image(file_path: str, investigation_id: str | None = None) -> dict:
    """
    Run complete AIMD forensic analysis on an image.

    Includes:
    - File information
    - SHA-256 hash
    - Perceptual hash
    - Metadata analysis
    - Frequency analysis
    - Compression analysis
    - Noise analysis
    - ML-based AI image detection
    """

    path = Path(file_path)

    # -----------------------------
    # Validate file
    # -----------------------------
    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Path is not a file: {file_path}"
        )

    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError(
            "Forensic image analyzer currently "
            "supports JPG, JPEG, PNG and WEBP."
        )

    # -----------------------------
    # Metadata Analysis
    # -----------------------------
    print("[AIMD] Extracting metadata...")

    metadata = _run_signal(extract_metadata, file_path, "Metadata")

    # -----------------------------
    # SHA-256 Hash
    # -----------------------------
    print("[AIMD] Generating SHA-256...")

    sha256 = _run_signal(sha256_file, file_path, "SHA-256")

    # -----------------------------
    # Perceptual Hash
    # -----------------------------
    print("[AIMD] Generating perceptual hash...")

    phash = _run_signal(phash_image, file_path, "Perceptual hash")

    # -----------------------------
    # Frequency Analysis
    # -----------------------------
    print("[AIMD] Running frequency analysis...")

    frequency = _run_signal(frequency_analysis, file_path, "Frequency")

    # -----------------------------
    # Compression Analysis
    # -----------------------------
    print("[AIMD] Running compression analysis...")

    compression = _run_signal(compression_analysis, file_path, "Compression")

    # -----------------------------
    # Noise Analysis
    # -----------------------------
    print("[AIMD] Running noise analysis...")

    noise = _run_signal(noise_analysis, file_path, "Noise")

    # -----------------------------
    # ML AI Detection
    # -----------------------------
    print("[AIMD] Running ML AI detector...")

    ml_result = _run_ml_detector(file_path)

    fingerprints = {
        "sha256": sha256,
        "phash": phash,
    }
    forensic_features = {
        "frequency": frequency,
        "compression": compression,
        "noise": noise,
    }
    provenance = trace_provenance(
        file_path=file_path,
        fingerprints=fingerprints,
        metadata=metadata,
        compression=compression,
        media_id=investigation_id or path.stem,
    )
    ensemble = assess_ensemble(
        ml_detection=ml_result,
        metadata=metadata,
        forensic_features=forensic_features,
        fingerprints=fingerprints,
    )

    # -----------------------------
    # Final Result
    # -----------------------------
    return {
        "analysis_version": "0.4.0",
        "investigation_id": investigation_id or path.stem,

        "file": {
            "name": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
        },

        "fingerprints": fingerprints,

        "metadata": metadata,

        "forensic_features": forensic_features,

        "ml_detection": ml_result,
        "evidence": ensemble["signals"],
        "ensemble": ensemble,
        "provenance": provenance,
    }