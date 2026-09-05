import hashlib
import cv2
import numpy as np


def sha256_file(file_path: str) -> str:
    """
    Generate SHA-256 hash of the original file.
    Useful for exact file identification.
    """

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        while chunk := file.read(1024 * 1024):
            sha256.update(chunk)

    return sha256.hexdigest()


def phash_image(file_path: str) -> str:
    """
    Generate a simple perceptual hash.

    Unlike SHA-256, pHash can help identify visually similar
    versions after resizing/compression.
    """

    image = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)

    if image is None:
        raise ValueError("Unable to read image")

    # Resize to 32x32
    image = cv2.resize(image, (32, 32))

    # Convert to float
    image = np.float32(image)

    # DCT
    dct = cv2.dct(image)

    # Take low-frequency 8x8 region
    dct_low = dct[:8, :8]

    # Median excluding DC coefficient
    median = np.median(dct_low[1:, :])

    bits = dct_low > median

    # Convert 64 bits to hexadecimal
    hash_value = 0

    for bit in bits.flatten():
        hash_value = (hash_value << 1) | int(bit)

    return f"{hash_value:016x}"