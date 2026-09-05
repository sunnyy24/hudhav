# AIMD Methodology

AIMD combines file identity, image metadata, forensic measurements, and an open-weight image classifier into an explainable investigation response. The result is probabilistic evidence, not proof of origin or manipulation.

## Analysis Pipeline

1. Validate and store the uploaded artifact under a UUID-based filename.
2. Extract SHA-256 and perceptual fingerprints.
3. Extract image dimensions, format, and available EXIF metadata.
4. Calculate frequency-domain, compression-boundary, and noise-residual measurements.
5. Run the configured image classifier when its dependencies and model are available.
6. Normalize each result into an evidence object with status, strength, summary, and technical details.
7. Produce an ensemble assessment with a verdict, baseline confidence, reasoning, and limitations.

## Signals

The ML signal uses the model-provided AI and human probabilities when both values are available. Frequency, compression, and noise measurements are currently reported as contextual evidence. AIMD does not convert their raw values into anomaly percentages because no representative calibration dataset or validated thresholds are available.

Metadata and fingerprints help describe the artifact and its identity. Missing metadata is not interpreted as evidence of AI generation. Provenance is reported as unavailable unless a verified source is connected.

## Baseline Ensemble

The current ensemble is a transparent hackathon baseline. A strong, internally consistent ML signal can produce a directional assessment. Ambiguous, conflicting, or unavailable ML evidence produces `INCONCLUSIVE`. Other forensic signals remain visible and are included in reasoning, but they do not receive invented directional weights.

The confidence field is labeled:

> Baseline ensemble confidence; not a calibrated probability.

The baseline must be calibrated against a representative validation dataset before it is used for consequential decisions or presented as a scientific measurement.

## Verdicts

- `LIKELY AI-GENERATED`: the available ML evidence is strongly directional toward AI generation.
- `LIKELY AUTHENTIC`: the available ML evidence is strongly directional toward human-created media.
- `POTENTIALLY AI-ALTERED`: reserved for a future validated manipulation signal; it is not inferred by the current implementation.
- `INCONCLUSIVE`: evidence is unavailable, weak, conflicting, or insufficient for a directional assessment.

## Model Transparency

The classifier is an external open-weight model integration and is not an AIMD-created model. Its identity and limitations must be disclosed separately in `MODEL_DISCLOSURE.md` when the model is enabled.