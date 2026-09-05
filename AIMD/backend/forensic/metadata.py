from PIL import Image
from pathlib import Path


def extract_metadata(file_path: str) -> dict:
    """
    Extract basic image metadata and EXIF information.
    """

    path = Path(file_path)

    result = {
        "filename": path.name,
        "extension": path.suffix.lower(),
        "file_size_bytes": path.stat().st_size,
        "format": None,
        "width": None,
        "height": None,
        "mode": None,
        "exif_present": False,
        "exif": {}
    }

    try:
        image = Image.open(file_path)

        result["format"] = image.format
        result["width"] = image.width
        result["height"] = image.height
        result["mode"] = image.mode

        exif_data = image.getexif()

        if exif_data:
            result["exif_present"] = True

            for key, value in exif_data.items():
                try:
                    result["exif"][str(key)] = str(value)
                except Exception:
                    result["exif"][str(key)] = "unreadable"

    except Exception as error:
        result["error"] = str(error)

    return result