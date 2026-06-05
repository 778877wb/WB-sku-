"""Unit tests for dashboard API-ready structures."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from wb_ops.db.database import Base
from wb_ops.repositories.sku_repository import SkuRepository
from wb_ops.services.dashboard_service import DashboardService
from wb_ops.services.metrics_service import MetricsService
from wb_ops.services.sku_assignment_service import SkuAssignmentService


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with TestingSessionLocal() as session:
        yield session


def test_sales_statistics(db_session: Session) -> None:
    sku = SkuRepository(db_session).create("SKU-001", "Product", "Beauty")
    db_session.commit()
    MetricsService(db_session).record_daily_metrics(
        sku_id=sku.id,
        metric_date=date(2026, 6, 4),
        sales=10,
        revenue=Decimal("100.00"),
        orders=12,
        returns=1,
    )

    stats = DashboardService(db_session).sales_statistics(date(2026, 6, 1), date(2026, 6, 30))

    assert stats.to_dict()["total_sales"] == 10
    assert stats.total_revenue == Decimal("100.00")
    assert stats.total_orders == 12
    assert stats.total_returns == 1


def test_operator_performance_and_assignment_statistics(db_session: Session) -> None:
    assignment_service = SkuAssignmentService(db_session)
    operator = assignment_service.create_operator("运营A")
    assistant = assignment_service.create_operator("运营B")
    sku = assignment_service.create_sku("SKU-001", "Product", "Beauty")
    assignment_service.create_sku("SKU-002", "Product 2", "Beauty")
    assignment_service.assign_sku(sku.id, operator.id, role="owner")
    assignment_service.assign_sku(sku.id, assistant.id, role="assistant")

    dashboard = DashboardService(db_session)
    performance = dashboard.operator_performance()
    assignment_stats = dashboard.sku_assignment_statistics()

    assert [(item.operator_name, item.assigned_sku_count, item.owner_sku_count) for item in performance] == [
        ("运营A", 1, 1),
        ("运营B", 1, 0),
    ]
    assert assignment_stats.total_skus == 2
    assert assignment_stats.assigned_skus == 1
    assert assignment_stats.unassigned_skus == 1
    assert assignment_stats.assignments_by_role == {"assistant": 1, "owner": 1}


def test_inventory_statistics(db_session: Session) -> None:
    sku_repo = SkuRepository(db_session)
    sku_1 = sku_repo.create("SKU-001", "Product", "Beauty")
    sku_2 = sku_repo.create("SKU-002", "Product 2", "Beauty")
    db_session.commit()
    metrics = MetricsService(db_session)
    metrics.record_inventory_metrics(sku_id=sku_1.id, metric_date=date(2026, 6, 4), inventory_quantity=3)
    metrics.record_inventory_metrics(sku_id=sku_2.id, metric_date=date(2026, 6, 4), inventory_quantity=50)

    stats = DashboardService(db_session).inventory_statistics(date(2026, 6, 4), low_inventory_threshold=10)

    assert stats.total_inventory_quantity == 53
    assert stats.sku_count_with_inventory == 2
    assert stats.low_inventory_sku_count == 1
