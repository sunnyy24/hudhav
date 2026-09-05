from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import uuid
from PIL import Image, UnidentifiedImageError
from forensic.analyzer import analyze_image

router = APIRouter(prefix="/api", tags=["Media"])

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv"
}


@router.post("/upload")
async def upload_media(file: UploadFile = File(...)):

    original_filename = file.filename or ""
    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {extension}"
        )

    file_id = str(uuid.uuid4())
    filename = f"{file_id}{extension}"

    file_path = UPLOAD_DIR / filename

    total_bytes = 0

    try:
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                total_bytes += len(chunk)

                if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="File exceeds the 25 MB upload limit"
                    )

                buffer.write(chunk)

        if total_bytes == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        if extension in {".jpg", ".jpeg", ".png", ".webp"}:
            try:
                with Image.open(file_path) as image:
                    image.verify()
            except (UnidentifiedImageError, OSError) as error:
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file is not a valid image"
                ) from error

    except HTTPException:
        file_path.unlink(missing_ok=True)
        raise
    except OSError as error:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail="Unable to store uploaded file"
        ) from error

    return {
        "success": True,
        "file_id": file_id,
        "original_filename": original_filename,
        "stored_filename": filename,
        "file_type": extension,
        "message": "File uploaded successfully"
    }
@router.get("/analyze/{file_id}")
async def analyze_uploaded_image(file_id: str):
    """
    Run AIMD forensic analysis on an uploaded image.
    """

    try:
        normalized_file_id = str(uuid.UUID(file_id))
    except ValueError as error:
        raise HTTPException(status_code=404, detail="File not found") from error

    matching_files = [
        UPLOAD_DIR / f"{normalized_file_id}{extension}"
        for extension in ALLOWED_EXTENSIONS
        if (UPLOAD_DIR / f"{normalized_file_id}{extension}").is_file()
    ]

    if not matching_files:
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    file_path = matching_files[0]

    try:
        result = analyze_image(
            str(file_path),
            investigation_id=normalized_file_id,
        )

        return {
            "success": True,
            "file_id": file_id,
            "analysis": result
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to complete forensic analysis"
        )
if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m forensic.analyzer <image_path>")
        sys.exit(1)

    result = analyze_image(sys.argv[1])
    print(json.dumps(result, indent=2))