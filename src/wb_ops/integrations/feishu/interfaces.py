"""Placeholder interfaces for future Feishu synchronization features."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from wb_ops.integrations.feishu.client import FeishuApiClient


@dataclass(slots=True)
class FeishuOperationResult:
    """Generic placeholder operation result."""

    success: bool
    message: str
    payload: dict[str, Any] | None = None


class FeishuUserSync:
    def __init__(self, client: FeishuApiClient) -> None:
        self.client = client

    def sync_users(self) -> FeishuOperationResult:
        return FeishuOperationResult(success=False, message="User sync placeholder; Feishu credentials are not required yet.")


class FeishuOperatorSync:
    def __init__(self, client: FeishuApiClient) -> None:
        self.client = client

    def sync_operators(self) -> FeishuOperationResult:
        return FeishuOperationResult(success=False, message="Operator sync placeholder; mapping will be implemented later.")


class FeishuNotificationSender:
    def __init__(self, client: FeishuApiClient) -> None:
        self.client = client

    def send_notification(self, recipient: str, message: str) -> FeishuOperationResult:
        return FeishuOperationResult(
            success=False,
            message="Notification sending placeholder; no Feishu credentials required.",
            payload={"recipient": recipient, "message": message},
        )


class FeishuReportSender:
    def __init__(self, client: FeishuApiClient) -> None:
        self.client = client

    def send_report(self, report_name: str, data: dict[str, Any]) -> FeishuOperationResult:
        return FeishuOperationResult(
            success=False,
            message="Report sending placeholder; no Feishu credentials required.",
            payload={"report_name": report_name, "data": data},
        )
