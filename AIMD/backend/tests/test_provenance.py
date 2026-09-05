import tempfile
import unittest
from pathlib import Path

from PIL import Image

from forensic.hashing import phash_image, sha256_file
from provenance.c2pa import inspect_content_credentials
from provenance.engine import metadata_origin, platform_processing_evidence, trace_provenance
from provenance.repository import ProvenanceRepository
from provenance.similarity import phash_hamming_distance, perceptual_match


class ProvenanceTests(unittest.TestCase):

    def create_image(self, directory: str, name: str, color=(20, 40, 80), image_format="PNG") -> Path:
        path = Path(directory) / name
        Image.new("RGB", (32, 32), color).save(path, format=image_format)
        return path

    def test_exact_sha256_match(self):
        with tempfile.TemporaryDirectory() as directory:
            first = self.create_image(directory, "first.png")
            second = Path(directory) / "copy.png"
            second.write_bytes(first.read_bytes())
            repository = ProvenanceRepository(Path(directory) / "provenance.sqlite3")
            repository.record_media("first", sha256_file(str(first)), phash_image(str(first)))

            matches = repository.find_exact(sha256_file(str(second)), exclude_media_id="second")

        self.assertEqual(matches[0]["match_type"], "EXACT")
        self.assertEqual(matches[0]["match_strength"], "STRONG")

    def test_different_sha256_does_not_match(self):
        with tempfile.TemporaryDirectory() as directory:
            first = self.create_image(directory, "first.png", (20, 40, 80))
            second = self.create_image(directory, "second.png", (200, 10, 10))
            repository = ProvenanceRepository(Path(directory) / "provenance.sqlite3")
            repository.record_media("first", sha256_file(str(first)), phash_image(str(first)))

            matches = repository.find_exact(sha256_file(str(second)), exclude_media_id="second")

        self.assertEqual(matches, [])

    def test_phash_similarity_and_non_match(self):
        self.assertEqual(phash_hamming_distance("0f", "0f"), 0)
        self.assertTrue(perceptual_match("0f", "0e", threshold=1))
        self.assertFalse(perceptual_match("0f", "f0", threshold=1))

    def test_missing_and_present_metadata(self):
        missing = metadata_origin({"exif_present": False, "exif": {}})
        present = metadata_origin({"exif_present": True, "exif": {"271": "Canon", "272": "EOS"}})

        self.assertEqual(missing["camera_make"]["status"], "UNKNOWN")
        self.assertEqual(present["capture_device"], {"status": "VERIFIED", "value": "Canon EOS"})

    def test_missing_c2pa_is_unknown(self):
        result = inspect_content_credentials("unused.png")

        self.assertEqual(result["status"], "UNKNOWN")
        self.assertFalse(result["present"])

    def test_available_c2pa_reader_is_verified(self):
        result = inspect_content_credentials("unused.png", reader=lambda _: {"claim": "fixture"})

        self.assertEqual(result["status"], "VERIFIED")
        self.assertTrue(result["present"])
        self.assertEqual(result["details"]["claim"], "fixture")

    def test_possible_reencoding_is_inferred(self):
        result = platform_processing_evidence(
            "image.jpg",
            {"exif_present": False},
            {"vertical_block_boundary_mean": 4.2},
        )

        self.assertEqual(result["status"], "INFERRED")
        self.assertEqual(result["platform_processing"], "POSSIBLE")

    def test_no_provenance_available(self):
        with tempfile.TemporaryDirectory() as directory:
            image = self.create_image(directory, "image.png")
            result = trace_provenance(
                str(image),
                media_id="image",
                repository=ProvenanceRepository(Path(directory) / "provenance.sqlite3"),
            )

        self.assertEqual(result["matches"], [])
        self.assertEqual(result["origin"]["match_type"], "NONE")
        self.assertFalse(result["external_search"]["performed"])

    def test_multiple_evidence_records_are_returned(self):
        with tempfile.TemporaryDirectory() as directory:
            image = self.create_image(directory, "image.png")
            result = trace_provenance(
                str(image),
                media_id="image",
                repository=ProvenanceRepository(Path(directory) / "provenance.sqlite3"),
            )

        self.assertGreaterEqual(len(result["findings"]), 5)
        self.assertTrue(all("type" in item and "status" in item for item in result["findings"]))


if __name__ == "__main__":
    unittest.main()