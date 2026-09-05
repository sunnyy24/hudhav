from typing import Protocol

from origin.models import ProviderResult


class OriginProvider(Protocol):
    name: str

    async def search(self, image: bytes, filename: str | None = None) -> ProviderResult:
        ...