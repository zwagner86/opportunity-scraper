from __future__ import annotations

import os
from typing import Any

import requests


API_BASE_URL = os.getenv("OPPORTUNITY_API_BASE_URL", "http://localhost:8000/api")


class APIClient:
    def __init__(self, base_url: str = API_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def get(self, path: str, **params: Any) -> Any:
        response = self.session.get(f"{self.base_url}{path}", params=self._clean_params(params), timeout=30)
        response.raise_for_status()
        return response.json()

    def get_text(self, path: str, **params: Any) -> str:
        response = self.session.get(f"{self.base_url}{path}", params=self._clean_params(params), timeout=30)
        response.raise_for_status()
        return response.text

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        response = self.session.post(f"{self.base_url}{path}", json=payload, timeout=120)
        response.raise_for_status()
        return response.json()

    def patch(self, path: str, payload: dict[str, Any]) -> Any:
        response = self.session.patch(f"{self.base_url}{path}", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def _clean_params(self, params: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in params.items() if value not in (None, "")}
