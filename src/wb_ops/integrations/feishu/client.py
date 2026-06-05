"""Feishu API client abstraction for future concrete integrations."""

from __future__ import annotations

from typing import Any

import httpx

from wb_ops.integrations.feishu.config import FeishuConfig


class FeishuIntegrationError(RuntimeError):
    """Raised for Feishu integration errors."""


class FeishuApiClient:
    """Minimal Feishu client abstraction.

    Phase 5 does not require real credentials. Network calls are only made when
    the loaded config has ``enabled=True``.
    """

    def __init__(self, config: FeishuConfig) -> None:
        self.config = config

    def is_enabled(self) -> bool:
        return self.config.enabled

    def request(self, method: str, path: str, *, json: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.config.enabled:
            raise FeishuIntegrationError("Feishu integration is disabled; configure credentials and FEISHU_ENABLED=true")
        response = httpx.request(
            method,
            f"{self.config.base_url}/{path.lstrip('/')}",
            json=json,
            timeout=self.config.request_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()
