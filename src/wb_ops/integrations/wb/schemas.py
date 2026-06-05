"""Lightweight schemas for Wildberries product card synchronization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def normalize_vendor_code(value: str | None) -> str:
    """Normalize WB vendorCode before matching it to ``sku_pool.sku``."""

    return (value or "").strip()


@dataclass(frozen=True, slots=True)
class ProductCard:
    """WB product card fields required for listing detection.

    ``vendor_code`` maps to the local SKU code and ``nm_id`` maps to WB's
    nomenclature ID. The raw payload is kept for future Phase 3/4 enrichment.
    """

    vendor_code: str
    nm_id: int
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api_payload(cls, payload: dict[str, Any]) -> "ProductCard | None":
        """Build a card from a WB API payload.

        WB responses have historically used both ``nmID`` and ``nmId`` casing
        in examples and integrations, so both are accepted defensively.
        """

        vendor_code = normalize_vendor_code(payload.get("vendorCode"))
        nm_id = payload.get("nmID", payload.get("nmId"))
        if not vendor_code or nm_id in (None, ""):
            return None
        return cls(vendor_code=vendor_code, nm_id=int(nm_id), raw=payload)
