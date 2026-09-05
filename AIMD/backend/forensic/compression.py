import cv2
import numpy as np


def compression_analysis(file_path: str) -> dict:
    """
    Extract basic compression-related signals.

    These are forensic clues, not proof of manipulation.
    """

    image = cv2.imread(file_path)

    if image is None:
        raise ValueError("Unable to read image")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # JPEG block-boundary analysis
    h, w = gray.shape

    vertical_boundaries = []
    horizontal_boundaries = []

    # Compare pixels around 8x8 boundaries
    for x in range(8, w, 8):
        if x < w:
            difference = np.mean(
                np.abs(
                    gray[:, x].astype(float)
                    - gray[:, x - 1].astype(float)
                )
            )
            vertical_boundaries.append(difference)

    for y in range(8, h, 8):
        if y < h:
            difference = np.mean(
                np.abs(
                    gray[y, :].astype(float)
                    - gray[y - 1, :].astype(float)
                )
            )
            horizontal_boundaries.append(difference)

    return {
        "vertical_block_boundary_mean": round(
            float(np.mean(vertical_boundaries))
            if vertical_boundaries else 0,
            4
        ),
        "horizontal_block_boundary_mean": round(
            float(np.mean(horizontal_boundaries))
            if horizontal_boundaries else 0,
            4
        ),
        "image_width": w,
        "image_height": h
    }