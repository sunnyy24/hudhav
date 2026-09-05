import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from io import BytesIO
from urllib.error import HTTPError, URLError
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from origin.models import OriginMatch, ProviderResult
from origin.policy import is_external_search_enabled, is_google_provider_configured
from origin.providers.google_web_detection import GoogleWebDetectionProvider
from origin.routes import ConsentRequest, search_origin
from origin.service import OriginSearchRepository, search_external_origin


class FakeProvider:
    name = "fake_provider"

    def __init__(self, result):
        self.result = result
        self.calls = 0

    async def search(self, image: bytes, filename: str | None = None) -> ProviderResult:
        self.calls += 1
        return self.result


class OriginTests(unittest.TestCase):

    def run_async(self, operation):
        return asyncio.run(operation)

    def test_consent_missing_and_false(self):
        with self.assertRaises(HTTPException) as missing:
            self.run_async(search_origin("not-a-uuid", None))
        with self.assertRaises(HTTPException) as false:
            self.run_async(search_origin("not-a-uuid", ConsentRequest(consent=False)))

        self.assertEqual(missing.exception.status_code, 400)
        self.assertEqual(false.exception.status_code, 400)
        self.assertIn("explicit user consent", missing.exception.detail)

    def test_external_search_disabled(self):
        with patch.dict("os.environ", {"ORIGIN_SEARCH_ENABLED": "false"}, clear=False):
            response = self.run_async(
                search_origin("00000000-0000-0000-0000-000000000001", ConsentRequest(consent=True))
            )

        self.assertEqual(response["status"], "UNAVAILABLE")
        self.assertEqual(response["matches"], [])

    def test_policy_and_missing_google_credentials(self):
        with patch.dict("os.environ", {"ORIGIN_SEARCH_ENABLED": "false", "GOOGLE_VISION_API_KEY": ""}, clear=False):
            self.assertFalse(is_external_search_enabled())
            self.assertFalse(is_google_provider_configured())

        result = self.run_async(GoogleWebDetectionProvider(api_key="").search(b"image"))
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.error, "Google Web Detection is not configured.")

    def test_provider_unavailable(self):
        result = self.run_async(GoogleWebDetectionProvider(api_key=None).search(b"image"))
        self.assertEqual(result.status, "UNAVAILABLE")

    def test_google_exact_partial_perceptual_and_platform_mapping(self):
        response = {
            "responses": [{
                "webDetection": {
                    "pagesWithMatchingImages": [
                        {
                            "url": "https://www.instagram.com/p/example",
                            "pageTitle": "Instagram source",
                            "fullMatchingImages": [{"url": "https://cdn.example/exact.jpg"}],
                        },
                        {
                            "url": "https://example.com/partial",
                            "pageTitle": "Partial source",
                            "partialMatchingImages": [{"url": "https://cdn.example/partial.jpg"}],
                        },
                    ],
                    "visuallySimilarImages": [{"url": "https://www.youtube.com/watch?v=example"}],
                }
            }]
        }

        class Response:
            def read(self):
                import json
                return json.dumps(response).encode("utf-8")

        result = self.run_async(GoogleWebDetectionProvider(api_key="fixture", request_function=lambda *_args, **_kwargs: Response()).search(b"image"))

        self.assertEqual(result.status, "VERIFIED")
        self.assertEqual([match.match_type for match in result.matches], ["EXACT", "PARTIAL", "PERCEPTUAL"])
        self.assertEqual(result.matches[0].platform, "Instagram")
        self.assertEqual(result.matches[2].platform, "YouTube")
        self.assertIsNone(result.matches[1].first_seen)

    def test_google_multiple_pages(self):
        response = {"responses": [{"webDetection": {"pagesWithMatchingImages": [
            {"url": "https://one.example/a", "fullMatchingImages": [{"url": "https://one.example/image"}]},
            {"url": "https://two.example/b", "partialMatchingImages": [{"url": "https://two.example/image"}]},
        ]}}]}

        class Response:
            def read(self):
                import json
                return json.dumps(response).encode("utf-8")

        result = self.run_async(GoogleWebDetectionProvider(api_key="fixture", request_function=lambda *_args, **_kwargs: Response()).search(b"image"))
        self.assertEqual(len(result.matches), 2)

    def test_google_no_matches_and_malformed_response(self):
        class EmptyResponse:
            def read(self):
                return b'{"responses":[{"webDetection":{}}]}'

        class MalformedResponse:
            def read(self):
                return b"not-json"

        empty = self.run_async(GoogleWebDetectionProvider(api_key="fixture", request_function=lambda *_args, **_kwargs: EmptyResponse()).search(b"image"))
        malformed = self.run_async(GoogleWebDetectionProvider(api_key="fixture", request_function=lambda *_args, **_kwargs: MalformedResponse()).search(b"image"))
        self.assertEqual(empty.status, "UNKNOWN")
        self.assertEqual(malformed.status, "ERROR")

    def test_google_http_error_mapping(self):
        for code, expected in ((401, "Google Web Detection authorization failed."), (403, "Google Web Detection authorization failed."), (429, "Google Web Detection rate limit reached."), (500, "Google Web Detection service error.")):
            def request(*_args, code=code, **_kwargs):
                raise HTTPError("https://vision.googleapis.com", code, "provider detail", {}, BytesIO())

            result = self.run_async(GoogleWebDetectionProvider(api_key="fixture", request_function=request).search(b"image"))
            self.assertEqual(result.status, "ERROR")
            self.assertEqual(result.error, expected)

    def test_google_timeout_and_network_error(self):
        def timeout(*_args, **_kwargs):
            raise TimeoutError()

        def network(*_args, **_kwargs):
            raise URLError("offline")

        timeout_result = self.run_async(GoogleWebDetectionProvider(api_key="fixture", request_function=timeout).search(b"image"))
        network_result = self.run_async(GoogleWebDetectionProvider(api_key="fixture", request_function=network).search(b"image"))
        self.assertEqual(timeout_result.status, "ERROR")
        self.assertEqual(network_result.status, "ERROR")

    def test_provider_no_matches(self):
        result = ProviderResult("fake_provider", "UNKNOWN", "2026-01-01T00:00:00+00:00", error="No verified public source was discovered by this provider.")
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "image.png"
            image_path.write_bytes(b"image")
            with patch.dict("os.environ", {"ORIGIN_SEARCH_ENABLED": "true"}, clear=False):
                actual = self.run_async(search_external_origin("file-1", str(image_path), provider=FakeProvider(result), repository=OriginSearchRepository(Path(directory) / "origin.sqlite3")))

        self.assertEqual(actual.status, "UNKNOWN")
        self.assertEqual(actual.matches, [])

    def test_provider_one_and_multiple_matches(self):
        matches = [
            OriginMatch("https://example.com/one", title="One", match_type="EXACT", match_strength="VERIFIED"),
            OriginMatch("https://example.com/two", title="Two", match_type="PARTIAL", match_strength="INFERRED"),
        ]
        result = ProviderResult("fake_provider", "VERIFIED", "2026-01-01T00:00:00+00:00", matches=matches)
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "image.png"
            image_path.write_bytes(b"image")
            with patch.dict("os.environ", {"ORIGIN_SEARCH_ENABLED": "true"}, clear=False):
                actual = self.run_async(search_external_origin("file-2", str(image_path), provider=FakeProvider(result), repository=OriginSearchRepository(Path(directory) / "origin.sqlite3")))

        self.assertEqual(actual.status, "VERIFIED")
        self.assertEqual(len(actual.matches), 2)

    def test_provider_error(self):
        result = ProviderResult("fake_provider", "ERROR", "2026-01-01T00:00:00+00:00", error="Provider request failed.")
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "image.png"
            image_path.write_bytes(b"image")
            with patch.dict("os.environ", {"ORIGIN_SEARCH_ENABLED": "true"}, clear=False):
                actual = self.run_async(search_external_origin("file-3", str(image_path), provider=FakeProvider(result), repository=OriginSearchRepository(Path(directory) / "origin.sqlite3")))

        self.assertEqual(actual.status, "ERROR")
        self.assertEqual(actual.error, "Provider request failed.")

    def test_invalid_source_url_is_sanitized_and_key_is_not_returned(self):
        result = ProviderResult(
            "fake_provider",
            "VERIFIED",
            "2026-01-01T00:00:00+00:00",
            matches=[OriginMatch("javascript:alert(1)", title="Unsafe")],
            error="secret-api-key-should-not-appear",
        )
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "image.png"
            image_path.write_bytes(b"image")
            with patch.dict("os.environ", {"ORIGIN_SEARCH_ENABLED": "true"}, clear=False):
                actual = self.run_async(search_external_origin("file-4", str(image_path), provider=FakeProvider(result), repository=OriginSearchRepository(Path(directory) / "origin.sqlite3")))

        response = actual.to_dict()
        self.assertIsNone(response["matches"][0]["source_url"])
        self.assertNotIn("secret-api-key", str(response))

    def test_recent_success_is_cached(self):
        result = ProviderResult("fake_provider", "UNKNOWN", datetime.now(timezone.utc).isoformat())
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "image.png"
            image_path.write_bytes(b"image")
            repository = OriginSearchRepository(Path(directory) / "origin.sqlite3")
            provider = FakeProvider(result)
            with patch.dict("os.environ", {"ORIGIN_SEARCH_ENABLED": "true"}, clear=False):
                self.run_async(search_external_origin("file-5", str(image_path), provider=provider, repository=repository))
                self.run_async(search_external_origin("file-5", str(image_path), provider=provider, repository=repository))

        self.assertEqual(provider.calls, 1)


if __name__ == "__main__":
    unittest.main()