import cv2
import numpy as np


def frequency_analysis(file_path: str) -> dict:
    """
    Analyze frequency-domain characteristics of an image.
    """

    image = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)

    if image is None:
        raise ValueError("Unable to read image")

    image = cv2.resize(image, (256, 256))

    image_float = np.float32(image)

    # Remove average brightness
    image_float -= np.mean(image_float)

    # FFT
    fft = np.fft.fft2(image_float)
    fft_shift = np.fft.fftshift(fft)

    magnitude = np.abs(fft_shift)

    # Log transform
    magnitude_log = np.log1p(magnitude)

    # Normalize
    magnitude_norm = magnitude_log / (
        np.max(magnitude_log) + 1e-8
    )

    h, w = magnitude_norm.shape

    center_y = h // 2
    center_x = w // 2

    # Low-frequency region
    radius = 30

    y, x = np.ogrid[:h, :w]

    distance = np.sqrt(
        (x - center_x) ** 2 +
        (y - center_y) ** 2
    )

    low_frequency = magnitude_norm[distance <= radius]
    high_frequency = magnitude_norm[distance > radius]

    low_mean = float(np.mean(low_frequency))
    high_mean = float(np.mean(high_frequency))

    high_frequency_ratio = high_mean / (low_mean + 1e-8)

    return {
        "low_frequency_mean": round(low_mean, 6),
        "high_frequency_mean": round(high_mean, 6),
        "high_frequency_ratio": round(
            float(high_frequency_ratio), 6
        )
    }