"""Tests for the Feishu integration framework placeholders."""

from __future__ import annotations

import pytest

from wb_ops.integrations.feishu.client import FeishuApiClient, FeishuIntegrationError
from wb_ops.integrations.feishu.config import FeishuConfig, load_feishu_config
from wb_ops.integrations.feishu.interfaces import FeishuNotificationSender, FeishuOperatorSync, FeishuReportSender, FeishuUserSync


def test_feishu_config_defaults_do_not_require_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FEISHU_APP_ID", raising=False)
    config = load_feishu_config()

    assert config.enabled is False
    assert config.app_id == "FEISHU_APP_ID_PLACEHOLDER"


def test_disabled_client_does_not_make_network_calls() -> None:
    client = FeishuApiClient(FeishuConfig(enabled=False))

    assert client.is_enabled() is False
    with pytest.raises(FeishuIntegrationError, match="disabled"):
        client.request("GET", "/anything")


def test_placeholder_interfaces_return_structured_results() -> None:
    client = FeishuApiClient(FeishuConfig(enabled=False))

    assert FeishuUserSync(client).sync_users().success is False
    assert FeishuOperatorSync(client).sync_operators().success is False
    assert FeishuNotificationSender(client).send_notification("u1", "hello").payload == {"recipient": "u1", "message": "hello"}
    assert FeishuReportSender(client).send_report("daily", {"sales": 1}).payload == {"report_name": "daily", "data": {"sales": 1}}
