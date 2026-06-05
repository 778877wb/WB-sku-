"""Token and multi-store configuration for Wildberries API access."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_WB_CONFIG_PATH = Path("config/wb_tokens.json")


@dataclass(frozen=True, slots=True)
class StoreTokenConfig:
    """One Wildberries store and its token source."""

    shop_name: str
    api_token: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class WbIntegrationConfig:
    """Wildberries integration settings shared by all stores."""

    stores: tuple[StoreTokenConfig, ...]
    content_api_base_url: str = "https://content-api.wildberries.ru"
    request_timeout_seconds: int = 30
    cards_page_limit: int = 100
    mark_missing_cards_as_delisted: bool = False

    @property
    def enabled_stores(self) -> tuple[StoreTokenConfig, ...]:
        """Return stores enabled for synchronization."""

        return tuple(store for store in self.stores if store.enabled)


def _read_token(store_payload: dict[str, Any]) -> str:
    """Read a token directly or from an environment variable declared in JSON."""

    token = str(store_payload.get("api_token") or "").strip()
    token_env = str(store_payload.get("api_token_env") or "").strip()
    if token:
        return token
    if token_env:
        return os.getenv(token_env, "").strip()
    return ""


def load_wb_config(path: str | Path | None = None) -> WbIntegrationConfig:
    """Load Wildberries token configuration from JSON.

    The default path is ``config/wb_tokens.json`` and can be overridden by the
    ``WB_TOKENS_CONFIG`` environment variable. The repository contains
    ``config/wb_tokens.example.json`` as a safe template without real tokens.
    """

    config_path = Path(path or os.getenv("WB_TOKENS_CONFIG", DEFAULT_WB_CONFIG_PATH))
    with config_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    stores: list[StoreTokenConfig] = []
    for store_payload in payload.get("stores", []):
        shop_name = str(store_payload.get("shop_name") or "").strip()
        enabled = bool(store_payload.get("enabled", True))
        token = _read_token(store_payload)
        if not shop_name:
            raise ValueError("Every WB store config entry must include shop_name.")
        if enabled and not token:
            raise ValueError(f"WB API token is missing for enabled shop: {shop_name}")
        stores.append(StoreTokenConfig(shop_name=shop_name, api_token=token, enabled=enabled))

    if not stores:
        raise ValueError(f"No WB stores configured in {config_path}")

    return WbIntegrationConfig(
        stores=tuple(stores),
        content_api_base_url=str(payload.get("content_api_base_url") or "https://content-api.wildberries.ru").rstrip("/"),
        request_timeout_seconds=int(payload.get("request_timeout_seconds", 30)),
        cards_page_limit=int(payload.get("cards_page_limit", 100)),
        mark_missing_cards_as_delisted=bool(payload.get("mark_missing_cards_as_delisted", False)),
    )
