import cv2
import numpy as np


def noise_analysis(file_path: str) -> dict:
    """
    Estimate high-frequency noise/residual characteristics.
    """

    image = cv2.imread(file_path)

    if image is None:
        raise ValueError("Unable to read image")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Gaussian blur represents smooth component
    blurred = cv2.GaussianBlur(
        gray,
        (5, 5),
        0
    )

    # Residual = original - smooth component
    residual = (
        gray.astype(np.float32)
        - blurred.astype(np.float32)
    )

    residual_std = float(np.std(residual))
    residual_mean = float(np.mean(np.abs(residual)))

    # Edge density
    edges = cv2.Canny(
        gray,
        threshold1=100,
        threshold2=200
    )

    edge_density = float(
        np.count_nonzero(edges) / edges.size
    )

    return {
        "noise_std": round(residual_std, 6),
        "mean_noise_magnitude": round(
            residual_mean,
            6
        ),
        "edge_density": round(
            edge_density,
            6
        )
    }