# app/providers/registry.py

from typing import Dict, Type

from app.providers.base import TextProvider
from app.providers.fitz_provider import FitzWrapper
from app.providers.docling_provider import DoclingWrapper


class ProviderRegistry:

    def __init__(self) -> None:
        self._providers: Dict[str, Type[TextProvider]] = {}

    def register(self, name: str, cls: Type[TextProvider]) -> None:
        self._providers[name] = cls

    def get(self, name: str) -> Type[TextProvider]:
        if name not in self._providers:
            raise KeyError(
                f"Unknown provider '{name}'. Available: {list(self._providers)}"
            )
        return self._providers[name]

    def available(self) -> list[str]:
        return list(self._providers.keys())


# Module-level singleton — import `registry` everywhere that needs it.
# Providers are registered here at import time so the registry is always ready without any explicit startup call.
registry = ProviderRegistry()
registry.register("fitz",    FitzWrapper)
registry.register("docling", DoclingWrapper)
# registry.register("xyz", XYZWrapper)  ← uncomment when XYZ is implemented