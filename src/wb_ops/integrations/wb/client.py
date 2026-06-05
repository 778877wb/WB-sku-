"""Wildberries Content API client for product card synchronization."""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

import httpx

from wb_ops.integrations.wb.schemas import ProductCard


class WildberriesApiError(RuntimeError):
    """Raised when Wildberries API returns an error response."""


class WildberriesClient:
    """Client for WB Content API product card methods.

    Product Cards List is used for Phase 2 listing detection because it returns
    the seller article ``vendorCode`` and WB article ``nmID``.
    """

    def __init__(
        self,
        api_token: str,
        base_url: str = "https://content-api.wildberries.ru",
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ) -> None:
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self.api_token,
            "Content-Type": "application/json",
        }

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.post(url, headers=self._headers(), json=payload, timeout=self.timeout_seconds)
                if response.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                    time.sleep(2**attempt)
                    continue
                response.raise_for_status()
                data = response.json()
                if data.get("error"):
                    raise WildberriesApiError(str(data.get("errorText") or data.get("additionalErrors") or data))
                return data
            except (httpx.HTTPError, WildberriesApiError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(2**attempt)
        raise WildberriesApiError(f"Wildberries request failed: {last_error}")

    @staticmethod
    def _cards_payload(limit: int, cursor: dict[str, Any] | None = None) -> dict[str, Any]:
        settings: dict[str, Any] = {
            "sort": {"ascending": True},
            "filter": {"withPhoto": -1},
            "cursor": {"limit": limit},
        }
        if cursor:
            settings["cursor"].update(cursor)
        return {"settings": settings}

    def get_product_cards_page(self, limit: int = 100, cursor: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch one page from ``/content/v2/get/cards/list``."""

        return self._post("/content/v2/get/cards/list", self._cards_payload(limit=limit, cursor=cursor))

    def iter_product_cards(self, limit: int = 100) -> Iterator[ProductCard]:
        """Yield all product cards from WB using cursor pagination."""

        cursor: dict[str, Any] | None = None
        while True:
            payload = self.get_product_cards_page(limit=limit, cursor=cursor)
            cards_payload = payload.get("cards") or payload.get("data") or []
            for item in cards_payload:
                card = ProductCard.from_api_payload(item)
                if card is not None:
                    yield card

            response_cursor = payload.get("cursor") or {}
            total = int(response_cursor.get("total", len(cards_payload)))
            if total < limit or not cards_payload:
                break

            updated_at = response_cursor.get("updatedAt")
            nm_id = response_cursor.get("nmID", response_cursor.get("nmId"))
            if not updated_at or not nm_id:
                break
            cursor = {"updatedAt": updated_at, "nmID": nm_id}
