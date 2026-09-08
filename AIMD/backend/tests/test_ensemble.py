import unittest

from forensic.ensemble import assess_ensemble


def available_features():
    return {
        "frequency": {"high_frequency_ratio": 1.2},
        "compression": {"vertical_block_boundary_mean": 2.1},
        "noise": {"noise_std": 4.2},
    }


class EnsembleTests(unittest.TestCase):

    def test_strong_ml_ai_signal(self):
        result = assess_ensemble(
            ml_detection={
                "status": "available",
                "prediction": "AI-GENERATED",
                "confidence": 0.94,
                "ai_probability": 0.94,
                "human_probability": 0.06,
                "raw_scores": {"AI": 0.94, "Human": 0.06},
            },
            metadata={"format": "PNG"},
            forensic_features=available_features(),
        )

        self.assertEqual(result["verdict"], "LIKELY AI-GENERATED")
        self.assertEqual(result["evidence_strength"], "STRONG")
        self.assertEqual(result["confidence"], 0.94)
        self.assertEqual(
            result["verdict_explanation"],
            "ML classification is strongly directional toward AI generation.",
        )
        self.assertEqual(result["signals"][0]["name"], "ML Classification")
        self.assertEqual(result["signals"][0]["status"], "INFERRED")

    def test_strong_human_signal(self):
        result = assess_ensemble(
            ml_detection={
                "status": "available",
                "prediction": "HUMAN",
                "confidence": 0.91,
                "ai_probability": 0.09,
                "human_probability": 0.91,
                "raw_scores": {"AI": 0.09, "Human": 0.91},
            },
            metadata={"format": "JPEG"},
            forensic_features=available_features(),
        )

        self.assertEqual(result["verdict"], "LIKELY AUTHENTIC")
        self.assertEqual(result["confidence"], 0.91)

    def test_moderate_directional_ai_signal(self):
        result = assess_ensemble(
            ml_detection={
                "status": "available",
                "prediction": "AI-GENERATED",
                "confidence": 0.737457,
                "ai_probability": 0.737457,
                "human_probability": 0.262543,
                "raw_scores": {"REAL": 0.262543, "FAKE": 0.737457},
            },
            metadata={"format": "PNG"},
            forensic_features=available_features(),
        )

        self.assertEqual(result["verdict"], "LIKELY AI-GENERATED")
        self.assertEqual(result["evidence_strength"], "MODERATE")

    def test_conflicting_ml_signal_is_inconclusive(self):
        result = assess_ensemble(
            ml_detection={
                "status": "available",
                "prediction": "AI-GENERATED",
                "confidence": 0.80,
                "ai_probability": 0.80,
                "human_probability": 0.80,
                "raw_scores": {},
            },
            metadata={"format": "PNG"},
            forensic_features=available_features(),
        )

        self.assertEqual(result["verdict"], "INCONCLUSIVE")
        self.assertEqual(result["evidence_strength"], "WEAK")

    def test_missing_metadata_is_reported(self):
        result = assess_ensemble(
            ml_detection={"status": "unavailable", "reason": "model unavailable"},
            metadata=None,
            forensic_features=available_features(),
        )

        metadata_signal = next(signal for signal in result["signals"] if signal["name"] == "Metadata")
        self.assertEqual(metadata_signal["status"], "UNAVAILABLE")
        self.assertIn("metadata", " ".join(result["reasoning"]).lower())

    def test_failed_forensic_detector_isolated(self):
        result = assess_ensemble(
            ml_detection={"status": "unavailable", "reason": "model unavailable"},
            metadata={"format": "PNG"},
            forensic_features={
                "frequency": {"status": "unavailable", "reason": "detector failed"},
                "compression": available_features()["compression"],
                "noise": available_features()["noise"],
            },
        )

        frequency_signal = next(signal for signal in result["signals"] if signal["name"] == "Frequency Analysis")
        self.assertEqual(frequency_signal["status"], "UNAVAILABLE")
        self.assertEqual(result["verdict"], "INCONCLUSIVE")

    def test_missing_ml_detector_is_inconclusive(self):
        result = assess_ensemble(
            ml_detection={"status": "unavailable", "reason": "not installed"},
            metadata={"format": "PNG"},
            forensic_features=available_features(),
        )

        self.assertEqual(result["verdict"], "INCONCLUSIVE")
        self.assertEqual(result["confidence"], 0.10)

    def test_insufficient_evidence_is_inconclusive(self):
        result = assess_ensemble(
            ml_detection={
                "status": "available",
                "prediction": "INCONCLUSIVE",
                "confidence": 0.55,
                "ai_probability": 0.55,
                "human_probability": 0.45,
                "raw_scores": {},
            },
            metadata=None,
            forensic_features={},
        )

        self.assertEqual(result["verdict"], "INCONCLUSIVE")
        self.assertEqual(result["evidence_strength"], "WEAK")
        self.assertEqual(result["signals"][-1]["name"], "Online Origin Discovery")
        self.assertEqual(result["signals"][-1]["status"], "UNAVAILABLE")

    def test_local_provenance_is_included_when_provided(self):
        result = assess_ensemble(
            ml_detection={
                "status": "available",
                "prediction": "AI-GENERATED",
                "confidence": 0.94,
                "ai_probability": 0.94,
                "human_probability": 0.06,
                "raw_scores": {},
            },
            metadata={"format": "PNG", "width": 32, "height": 24},
            forensic_features=available_features(),
            fingerprints={"sha256": "abc", "phash": "def"},
            provenance={
                "identity": {"sha256": "abc", "phash": "def"},
                "matches": [{"media_id": "prior", "match_type": "EXACT"}],
                "content_credentials": {
                    "status": "UNAVAILABLE",
                    "present": False,
                    "reason": "Content Credentials inspection unavailable.",
                },
                "origin": {"status": "UNKNOWN"},
            },
        )

        provenance_signal = next(signal for signal in result["signals"] if signal["name"] == "Local Provenance")
        identity_signal = next(signal for signal in result["signals"] if signal["name"] == "File Identity")
        credentials_signal = next(signal for signal in result["signals"] if signal["name"] == "Content Credentials")
        self.assertEqual(provenance_signal["status"], "VERIFIED")
        self.assertEqual(identity_signal["status"], "VERIFIED")
        self.assertEqual(credentials_signal["status"], "UNAVAILABLE")

    def test_invalid_ml_input_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_ensemble(
                ml_detection=None,
                metadata=None,
                forensic_features={},
            )


if __name__ == "__main__":
    unittest.main()