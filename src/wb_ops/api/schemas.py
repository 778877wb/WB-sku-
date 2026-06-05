"""Pydantic request and response schemas for the FastAPI backend."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SkuCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=128)
    product_name: str = Field(min_length=1, max_length=255)
    category: str | None = None
    status: str = "待分配"


class SkuUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=128)
    product_name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = None
    status: str | None = None


class SkuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    product_name: str
    category: str | None = None
    status: str
    created_at: datetime


class OperatorCreate(BaseModel):
    operator_name: str = Field(min_length=1, max_length=128)
    status: str = "在职"


class OperatorUpdate(BaseModel):
    operator_name: str | None = Field(default=None, min_length=1, max_length=128)
    status: str | None = None


class OperatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operator_name: str
    status: str
    created_at: datetime


class AssignmentCreate(BaseModel):
    sku_id: int
    operator_id: int
    role: str = "owner"


class AssignmentDelete(BaseModel):
    operator_id: int
    role: str = "owner"


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku_id: int
    operator_id: int
    role: str
    assigned_at: datetime


class AssignmentHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku_id: int
    old_operator_id: int | None = None
    new_operator_id: int | None = None
    role: str
    action: str
    changed_at: datetime


class SalesStatisticsResponse(BaseModel):
    total_sales: int
    total_revenue: Decimal
    total_orders: int
    total_returns: int


class OperatorPerformanceResponse(BaseModel):
    operator_id: int
    operator_name: str
    assigned_sku_count: int
    owner_sku_count: int


class SkuAssignmentStatisticsResponse(BaseModel):
    total_skus: int
    assigned_skus: int
    unassigned_skus: int
    assignments_by_role: dict[str, int]


class InventoryStatisticsResponse(BaseModel):
    total_inventory_quantity: int
    sku_count_with_inventory: int
    low_inventory_sku_count: int


class HealthResponse(BaseModel):
    status: str
    service: str


class ErrorResponse(BaseModel):
    detail: str | dict[str, Any]
