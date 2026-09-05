import os


def is_external_search_enabled() -> bool:
    return os.getenv("ORIGIN_SEARCH_ENABLED", "false").strip().lower() == "true"


def is_google_provider_configured() -> bool:
    return bool(os.getenv("GOOGLE_VISION_API_KEY", "").strip())