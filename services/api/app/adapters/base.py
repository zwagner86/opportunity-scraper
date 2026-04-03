from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.domain import FetchResult


class SourceAdapter(ABC):
    source_name: str

    @abstractmethod
    def fetch(self, *, run_id: int, limit_override: int | None = None) -> FetchResult:
        raise NotImplementedError

    @staticmethod
    def limit_value(configured: int | None, limit_override: int | None) -> int | None:
        if limit_override is not None:
            return limit_override
        return configured

