# AIMD Provenance Methodology

AIMD separates verified artifact identity from origin inference. The local provenance engine does not search social platforms and does not claim an origin without source evidence.

## Identity

- SHA-256 identifies exact byte-for-byte equality.
- pHash supports perceptual comparison after resizing or compression.
- Exact matches use SHA-256 equality.
- Perceptual matches use configurable pHash Hamming distance through `PHASH_MAX_DISTANCE`.

The default pHash threshold is a hackathon baseline and requires validation against representative media before consequential use. A perceptual match is not proof that two files share an origin.

## Local Repository

AIMD stores only media identity, sanitized source fields, observation time, and a small metadata summary in a local SQLite database. It does not copy uploaded media into the repository. A local match verifies that an earlier AIMD observation had the same identity or a similar pHash; it does not establish a public source URL.

## Metadata Origin

Known EXIF fields such as camera make, camera model, capture time, software, and GPS availability are surfaced as `VERIFIED` only when present in the file. Missing fields are `UNKNOWN`. Missing metadata is not evidence of AI generation.

## Content Credentials / C2PA

The C2PA adapter is optional. In the current environment no C2PA parser is installed, so the response explicitly reports that inspection is unavailable. The absence of a parsed credential is not interpreted as proof of AI generation.

## Platform Processing

JPEG block measurements and metadata availability can support an `INFERRED` statement such as possible re-encoding. These observations are not platform-specific. AIMD does not name Instagram, X, Facebook, TikTok, or another platform without verifiable external source evidence.

## Status Vocabulary

- `VERIFIED`: directly established from the artifact or local repository.
- `INFERRED`: a cautious interpretation of available local signals.
- `UNKNOWN`: not established, unavailable, or not searched.

AIMD does not claim that a media file originated from a social-media platform unless verifiable source evidence exists.