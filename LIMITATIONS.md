# AIMD Limitations

- AI detectors can produce false positives and false negatives.
- Performance can vary across image generators, editing tools, formats, and image content.
- Compression and social-media re-encoding can alter or erase forensic evidence.
- Absence of metadata is not proof of AI generation.
- Absence of Content Credentials is not proof of AI generation.
- The current ensemble confidence is a baseline assessment, not automatically a calibrated probability.
- Frequency, compression, and noise values do not have validated anomaly thresholds in the current implementation.
- The current implementation analyzes images; video and audio analysis are not yet implemented.
- Provenance is not inferred from a file hash or perceptual hash alone.
- The current system does not localize manipulated regions.
- Human review may be required for consequential decisions.