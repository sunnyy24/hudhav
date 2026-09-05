import importlib
import importlib.util
from collections.abc import Callable
from typing import Any


def c2pa_dependency_available() -> bool:
    return importlib.util.find_spec("c2pa") is not None


def inspect_content_credentials(
    file_path: str,
    reader: Callable[[str], dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Inspect C2PA only when a compatible parser is available or injected."""
    if reader is not None:
        try:
            details = reader(file_path)
        except Exception:
            return {
                "status": "UNKNOWN",
                "present": False,
                "reason": "Content Credentials inspection failed.",
            }

        if details:
            return {"status": "VERIFIED", "present": True, "details": details}
        return {
            "status": "UNKNOWN",
            "present": False,
            "reason": "No Content Credentials were detected.",
        }

    if not c2pa_dependency_available():
        return {
            "status": "UNKNOWN",
            "present": False,
            "reason": "C2PA inspection is unavailable because the optional c2pa library is not installed.",
        }

    try:
        c2pa_module = importlib.import_module("c2pa")
        reader_class = getattr(c2pa_module, "Reader", None)
        if reader_class is None:
            return {
                "status": "UNKNOWN",
                "present": False,
                "reason": "The installed c2pa library does not expose a supported Reader API.",
            }

        credential_reader = reader_class(file_path)
        details = credential_reader.get_manifest_store()
        if details:
            return {"status": "VERIFIED", "present": True, "details": details}
    except Exception:
        return {
            "status": "UNKNOWN",
            "present": False,
            "reason": "Content Credentials inspection failed.",
        }

    return {
        "status": "UNKNOWN",
        "present": False,
        "reason": "No Content Credentials were detected.",
    }