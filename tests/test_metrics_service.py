"""Unit tests for metrics services."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from wb_ops.db.database import Base
from wb_ops.db.models import AdvertisingMetrics, DailyMetrics, InventoryMetrics, SkuPool
from wb_ops.repositories.sku_repository import SkuRepository
from wb_ops.services.metrics_service import MetricsError, MetricsService


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with TestingSessionLocal() as session:
        yield session


@pytest.fixture()
def sku(db_session: Session) -> SkuPool:
    sku_item = SkuRepository(db_session).create("SKU-001", "Test product", "Beauty")
    db_session.commit()
    return sku_item


def test_record_daily_metrics_upserts(db_session: Session, sku: SkuPool) -> None:
    service = MetricsService(db_session)
    metric_date = date(2026, 6, 4)

    first = service.record_daily_metrics(sku_id=sku.id, metric_date=metric_date, sales=10, revenue=Decimal("99.90"), orders=12, returns=1)
    second = service.record_daily_metrics(sku_id=sku.id, metric_date=metric_date, sales=20, revenue=Decimal("199.90"), orders=22, returns=2)

    assert first.id == second.id
    assert second.sales == 20
    assert second.revenue == Decimal("199.90")
    assert db_session.query(DailyMetrics).count() == 1


def test_record_inventory_metrics(db_session: Session, sku: SkuPool) -> None:
    record = MetricsService(db_session).record_inventory_metrics(sku_id=sku.id, metric_date=date(2026, 6, 4), inventory_quantity=300)

    assert record.inventory_quantity == 300
    assert db_session.query(InventoryMetrics).count() == 1


def test_record_advertising_metrics(db_session: Session, sku: SkuPool) -> None:
    record = MetricsService(db_session).record_advertising_metrics(
        sku_id=sku.id,
        metric_date=date(2026, 6, 4),
        ad_spend=Decimal("123.45"),
        ctr=Decimal("0.1234"),
        cpc=Decimal("1.2345"),
    )

    assert record.ad_spend == Decimal("123.45")
    assert record.ctr == Decimal("0.1234")
    assert record.cpc == Decimal("1.2345")
    assert db_session.query(AdvertisingMetrics).count() == 1


def test_metrics_reject_negative_values(db_session: Session, sku: SkuPool) -> None:
    with pytest.raises(MetricsError, match="sales must be non-negative"):
        MetricsService(db_session).record_daily_metrics(
            sku_id=sku.id,
            metric_date=date(2026, 6, 4),
            sales=-1,
            revenue=Decimal("0"),
            orders=0,
            returns=0,
        )


def test_metrics_require_existing_sku(db_session: Session) -> None:
    with pytest.raises(MetricsError, match="SKU does not exist"):
        MetricsService(db_session).record_inventory_metrics(sku_id=999, metric_date=date(2026, 6, 4), inventory_quantity=1)


def test_metrics_tables_have_required_fields() -> None:
    assert {column.name for column in DailyMetrics.__table__.columns} >= {"id", "sku_id", "date", "sales", "revenue", "orders", "returns"}
    assert {column.name for column in InventoryMetrics.__table__.columns} >= {"id", "sku_id", "date", "inventory_quantity"}
    assert {column.name for column in AdvertisingMetrics.__table__.columns} >= {"id", "sku_id", "date", "ad_spend", "ctr", "cpc"}
