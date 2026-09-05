import asyncio
import base64
import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.parse import urlsplit

from origin.models import OriginMatch, ProviderResult
from provenance.repository import sanitize_source_url


GOOGLE_ANNOTATE_URL = "https://vision.googleapis.com/v1/images:annotate"


def _searched_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_provider_error(error: HTTPError) -> str:
    if error.code in {401, 403}:
        return "Google Web Detection authorization failed."
    if error.code == 429:
        return "Google Web Detection rate limit reached."
    if 500 <= error.code <= 599:
        return "Google Web Detection service error."
    return "Google Web Detection request failed."


def _platform_from_url(source_url: str | None) -> str | None:
    if not source_url:
        return None
    hostname = (urlsplit(source_url).hostname or "").lower().removeprefix("www.")
    platforms = {
        "instagram.com": "Instagram",
        "facebook.com": "Facebook",
        "x.com": "X",
        "twitter.com": "X",
        "tiktok.com": "TikTok",
        "youtube.com": "YouTube",
        "youtu.be": "YouTube",
        "reddit.com": "Reddit",
    }
    for domain, platform in platforms.items():
        if hostname == domain or hostname.endswith(f".{domain}"):
            return platform
    return None


class GoogleWebDetectionProvider:
    name = "google_web_detection"

    def __init__(self, api_key: str | None = None, request_function=urlopen):
        self.api_key = api_key if api_key is not None else os.getenv("GOOGLE_VISION_API_KEY", "").strip()
        self.request_function = request_function

    async def search(self, image: bytes, filename: str | None = None) -> ProviderResult:
        searched_at = _searched_at()
        if not self.api_key:
            return ProviderResult(
                provider=self.name,
                status="UNAVAILABLE",
                searched_at=searched_at,
                error="Google Web Detection is not configured.",
            )

        if not image:
            return ProviderResult(
                provider=self.name,
                status="ERROR",
                searched_at=searched_at,
                error="The image is empty.",
            )

        payload = {
            "requests": [
                {
                    "image": {"content": base64.b64encode(image).decode("ascii")},
                    "features": [{"type": "WEB_DETECTION", "maxResults": 10}],
                }
            ]
        }
        url = f"{GOOGLE_ANNOTATE_URL}?{urlencode({'key': self.api_key})}"
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            response = await asyncio.to_thread(self.request_function, request, timeout=20)
            response_data = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            return ProviderResult(self.name, "ERROR", searched_at, error=_safe_provider_error(error))
        except (URLError, TimeoutError):
            return ProviderResult(self.name, "ERROR", searched_at, error="Google Web Detection network request failed.")
        except (OSError, ValueError, json.JSONDecodeError):
            return ProviderResult(self.name, "ERROR", searched_at, error="Google Web Detection returned an invalid response.")

        if response_data.get("error"):
            return ProviderResult(self.name, "ERROR", searched_at, error="Google Web Detection returned an error.")

        web_detection = (response_data.get("responses") or [{}])[0].get("webDetection") or {}
        matches = self._matches_from_response(web_detection)
        if not matches:
            return ProviderResult(
                provider=self.name,
                status="UNKNOWN",
                searched_at=searched_at,
                error="No verified public source was discovered by this provider.",
            )

        return ProviderResult(self.name, "VERIFIED", searched_at, matches=matches)

    def _matches_from_response(self, web_detection: dict) -> list[OriginMatch]:
        matches: list[OriginMatch] = []
        for page in web_detection.get("pagesWithMatchingImages", []) or []:
            page_url = sanitize_source_url(page.get("url"))
            full_images = [item.get("url") for item in page.get("fullMatchingImages", []) or [] if item.get("url")]
            partial_images = [item.get("url") for item in page.get("partialMatchingImages", []) or [] if item.get("url")]
            match_type = "EXACT" if full_images else "PARTIAL" if partial_images else "UNKNOWN"
            source_url = page_url or sanitize_source_url((full_images or partial_images or [None])[0])
            if source_url is None:
                continue
            matches.append(
                OriginMatch(
                    source_url=source_url,
                    platform=_platform_from_url(source_url),
                    title=page.get("pageTitle"),
                    match_type=match_type,
                    match_strength="VERIFIED" if match_type == "EXACT" else "INFERRED" if match_type == "PARTIAL" else "UNKNOWN",
                    evidence={
                        "provider": self.name,
                        "matching_image_urls": full_images or partial_images,
                    },
                )
            )

        for image in web_detection.get("visuallySimilarImages", []) or []:
            source_url = sanitize_source_url(image.get("url"))
            if source_url is None:
                continue
            matches.append(
                OriginMatch(
                    source_url=source_url,
                    platform=_platform_from_url(source_url),
                    match_type="PERCEPTUAL",
                    match_strength="INFERRED",
                    evidence={"provider": self.name, "visual_similarity": True},
                )
            )

        return matches