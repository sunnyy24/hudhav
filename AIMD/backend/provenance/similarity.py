import os


DEFAULT_PHASH_MAX_DISTANCE = 10


def configured_phash_threshold() -> int:
    raw_threshold = os.getenv("PHASH_MAX_DISTANCE")
    if raw_threshold is None:
        return DEFAULT_PHASH_MAX_DISTANCE

    try:
        return max(0, int(raw_threshold))
    except ValueError:
        return DEFAULT_PHASH_MAX_DISTANCE


def phash_hamming_distance(first_hash: str, second_hash: str) -> int | None:
    if not isinstance(first_hash, str) or not isinstance(second_hash, str):
        return None

    try:
        return (int(first_hash, 16) ^ int(second_hash, 16)).bit_count()
    except ValueError:
        return None


def perceptual_match(first_hash: str, second_hash: str, threshold: int | None = None) -> bool:
    distance = phash_hamming_distance(first_hash, second_hash)
    if distance is None:
        return False
    return distance <= (configured_phash_threshold() if threshold is None else max(0, threshold))