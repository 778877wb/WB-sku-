"""Configuration placeholders for Feishu integration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeishuConfig:
    """Feishu API configuration.

    Credentials are optional placeholders in Phase 5 so tests and local
    development do not require a real Feishu app.
    """

    app_id: str = "FEISHU_APP_ID_PLACEHOLDER"
    app_secret: str = "FEISHU_APP_SECRET_PLACEHOLDER"
    bitable_app_token: str = "FEISHU_BITABLE_APP_TOKEN_PLACEHOLDER"
    base_url: str = "https://open.feishu.cn/open-apis"
    request_timeout_seconds: int = 30
    enabled: bool = False


def load_feishu_config() -> FeishuConfig:
    """Load Feishu placeholders from environment variables if present."""

    return FeishuConfig(
        app_id=os.getenv("FEISHU_APP_ID", "FEISHU_APP_ID_PLACEHOLDER"),
        app_secret=os.getenv("FEISHU_APP_SECRET", "FEISHU_APP_SECRET_PLACEHOLDER"),
        bitable_app_token=os.getenv("FEISHU_BITABLE_APP_TOKEN", "FEISHU_BITABLE_APP_TOKEN_PLACEHOLDER"),
        base_url=os.getenv("FEISHU_BASE_URL", "https://open.feishu.cn/open-apis").rstrip("/"),
        request_timeout_seconds=int(os.getenv("FEISHU_TIMEOUT_SECONDS", "30")),
        enabled=os.getenv("FEISHU_ENABLED", "false").lower() == "true",
    )
