"""API-ready dashboard statistics service layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from wb_ops.db.models import DailyMetrics, InventoryMetrics, Operator, SkuAssignment, SkuPool


@dataclass(slots=True)
class SalesStatistics:
    total_sales: int
    total_revenue: Decimal
    total_orders: int
    total_returns: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OperatorPerformance:
    operator_id: int
    operator_name: str
    assigned_sku_count: int
    owner_sku_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SkuAssignmentStatistics:
    total_skus: int
    assigned_skus: int
    unassigned_skus: int
    assignments_by_role: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class InventoryStatistics:
    total_inventory_quantity: int
    sku_count_with_inventory: int
    low_inventory_sku_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DashboardService:
    """Read-only service that returns API-ready dashboard structures."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def sales_statistics(self, start_date: date, end_date: date) -> SalesStatistics:
        row = self.db.execute(
            select(
                func.coalesce(func.sum(DailyMetrics.sales), 0),
                func.coalesce(func.sum(DailyMetrics.revenue), 0),
                func.coalesce(func.sum(DailyMetrics.orders), 0),
                func.coalesce(func.sum(DailyMetrics.returns), 0),
            ).where(DailyMetrics.date >= start_date, DailyMetrics.date <= end_date)
        ).one()
        return SalesStatistics(total_sales=int(row[0]), total_revenue=Decimal(row[1]), total_orders=int(row[2]), total_returns=int(row[3]))

    def operator_performance(self) -> list[OperatorPerformance]:
        operators = self.db.execute(select(Operator).order_by(Operator.id)).scalars().all()
        results: list[OperatorPerformance] = []
        for operator in operators:
            assigned_count = self.db.scalar(select(func.count()).select_from(SkuAssignment).where(SkuAssignment.operator_id == operator.id)) or 0
            owner_count = self.db.scalar(
                select(func.count()).select_from(SkuAssignment).where(SkuAssignment.operator_id == operator.id, SkuAssignment.role == "owner")
            ) or 0
            results.append(
                OperatorPerformance(
                    operator_id=operator.id,
                    operator_name=operator.operator_name,
                    assigned_sku_count=int(assigned_count),
                    owner_sku_count=int(owner_count),
                )
            )
        return results

    def sku_assignment_statistics(self) -> SkuAssignmentStatistics:
        total_skus = int(self.db.scalar(select(func.count()).select_from(SkuPool)) or 0)
        assigned_skus = int(self.db.scalar(select(func.count(func.distinct(SkuAssignment.sku_id)))) or 0)
        role_rows = self.db.execute(select(SkuAssignment.role, func.count()).group_by(SkuAssignment.role)).all()
        return SkuAssignmentStatistics(
            total_skus=total_skus,
            assigned_skus=assigned_skus,
            unassigned_skus=total_skus - assigned_skus,
            assignments_by_role={role: int(count) for role, count in role_rows},
        )

    def inventory_statistics(self, metric_date: date, low_inventory_threshold: int = 10) -> InventoryStatistics:
        records = self.db.execute(select(InventoryMetrics).where(InventoryMetrics.date == metric_date)).scalars().all()
        return InventoryStatistics(
            total_inventory_quantity=sum(item.inventory_quantity for item in records),
            sku_count_with_inventory=len(records),
            low_inventory_sku_count=sum(1 for item in records if item.inventory_quantity <= low_inventory_threshold),
        )
