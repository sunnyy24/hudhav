import tempfile
import unittest
from pathlib import Path

from PIL import Image

from detectors.image_detector import get_detector
from forensic.analyzer import analyze_image


class ForensicPipelineTests(unittest.TestCase):

    def test_image_analysis_returns_forensic_sections(self):
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "sample.png"
            Image.new("RGB", (32, 24), (120, 80, 40)).save(image_path)

            result = analyze_image(str(image_path))

        self.assertIn("fingerprints", result)
        self.assertEqual(len(result["fingerprints"]["sha256"]), 64)
        self.assertEqual(result["metadata"]["width"], 32)
        self.assertEqual(result["metadata"]["height"], 24)
        self.assertIn("frequency", result["forensic_features"])
        self.assertIn("compression", result["forensic_features"])
        self.assertIn("noise", result["forensic_features"])

    def test_detector_returns_structured_result(self):
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "detector.png"
            Image.new("RGB", (32, 24), (80, 120, 40)).save(image_path)
            result = get_detector().predict(str(image_path))

        self.assertIn(result["status"], {"available", "unavailable"})
        if result["status"] == "unavailable":
            self.assertEqual(result["prediction"], "INCONCLUSIVE")
        else:
            self.assertIn(result["prediction"], {"AI-GENERATED", "HUMAN"})
            self.assertIsNotNone(result["ai_probability"])
            self.assertIsNotNone(result["human_probability"])


if __name__ == "__main__":
    unittest.main()