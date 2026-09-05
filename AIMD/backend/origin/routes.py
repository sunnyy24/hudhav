from pathlib import Path
import uuid

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from origin.policy import is_external_search_enabled, is_google_provider_configured
from origin.service import search_external_origin, unavailable_result


router = APIRouter(prefix="/api/origin", tags=["Origin Discovery"])
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
CONSENT_MESSAGE = "External source discovery requires explicit user consent because the image may be transmitted to a third-party provider."


class ConsentRequest(BaseModel):
    consent: bool | None = None


def _find_image(file_id: str) -> Path:
    try:
        normalized_file_id = str(uuid.UUID(file_id))
    except ValueError as error:
        raise HTTPException(status_code=404, detail="File not found") from error

    for extension in IMAGE_EXTENSIONS:
        candidate = UPLOAD_DIR / f"{normalized_file_id}{extension}"
        if candidate.is_file():
            return candidate
    raise HTTPException(status_code=404, detail="File not found")


@router.post("/search/{file_id}")
async def search_origin(
    file_id: str,
    request: ConsentRequest | None = Body(default=None),
):
    if request is None or request.consent is not True:
        raise HTTPException(status_code=400, detail=CONSENT_MESSAGE)

    normalized_file_id = str(uuid.UUID(file_id)) if _is_uuid(file_id) else None
    if normalized_file_id is None:
        raise HTTPException(status_code=404, detail="File not found")

    if not is_external_search_enabled():
        result = unavailable_result("google_web_detection", "External origin discovery is disabled.")
        return {"file_id": normalized_file_id, **result.to_dict()}

    if not is_google_provider_configured():
        result = unavailable_result("google_web_detection", "Google Web Detection is not configured.")
        return {"file_id": normalized_file_id, **result.to_dict()}

    image_path = _find_image(normalized_file_id)
    result = await search_external_origin(
        file_id=normalized_file_id,
        image_path=str(image_path),
        filename=image_path.name,
    )
    return {"file_id": normalized_file_id, **result.to_dict()}


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True