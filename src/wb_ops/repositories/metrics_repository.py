"""Repositories for metrics tables."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from wb_ops.db.models import AdvertisingMetrics, DailyMetrics, InventoryMetrics


class DailyMetricsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_sku_date(self, sku_id: int, metric_date: date) -> DailyMetrics | None:
        return self.db.execute(select(DailyMetrics).where(DailyMetrics.sku_id == sku_id, DailyMetrics.date == metric_date)).scalar_one_or_none()

    def upsert(self, *, sku_id: int, metric_date: date, sales: int, revenue: Decimal, orders: int, returns: int) -> DailyMetrics:
        record = self.get_by_sku_date(sku_id, metric_date)
        if record is None:
            record = DailyMetrics(sku_id=sku_id, date=metric_date)
            self.db.add(record)
        record.sales = sales
        record.revenue = revenue
        record.orders = orders
        record.returns = returns
        self.db.flush()
        return record

    def list_by_date_range(self, start_date: date, end_date: date) -> list[DailyMetrics]:
        statement = select(DailyMetrics).where(DailyMetrics.date >= start_date, DailyMetrics.date <= end_date).order_by(DailyMetrics.date)
        return list(self.db.execute(statement).scalars().all())


class InventoryMetricsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_sku_date(self, sku_id: int, metric_date: date) -> InventoryMetrics | None:
        return self.db.execute(select(InventoryMetrics).where(InventoryMetrics.sku_id == sku_id, InventoryMetrics.date == metric_date)).scalar_one_or_none()

    def upsert(self, *, sku_id: int, metric_date: date, inventory_quantity: int) -> InventoryMetrics:
        record = self.get_by_sku_date(sku_id, metric_date)
        if record is None:
            record = InventoryMetrics(sku_id=sku_id, date=metric_date)
            self.db.add(record)
        record.inventory_quantity = inventory_quantity
        self.db.flush()
        return record

    def list_by_date_range(self, start_date: date, end_date: date) -> list[InventoryMetrics]:
        statement = select(InventoryMetrics).where(InventoryMetrics.date >= start_date, InventoryMetrics.date <= end_date).order_by(InventoryMetrics.date)
        return list(self.db.execute(statement).scalars().all())


class AdvertisingMetricsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_sku_date(self, sku_id: int, metric_date: date) -> AdvertisingMetrics | None:
        return self.db.execute(select(AdvertisingMetrics).where(AdvertisingMetrics.sku_id == sku_id, AdvertisingMetrics.date == metric_date)).scalar_one_or_none()

    def upsert(self, *, sku_id: int, metric_date: date, ad_spend: Decimal, ctr: Decimal, cpc: Decimal) -> AdvertisingMetrics:
        record = self.get_by_sku_date(sku_id, metric_date)
        if record is None:
            record = AdvertisingMetrics(sku_id=sku_id, date=metric_date)
            self.db.add(record)
        record.ad_spend = ad_spend
        record.ctr = ctr
        record.cpc = cpc
        self.db.flush()
        return record

    def list_by_date_range(self, start_date: date, end_date: date) -> list[AdvertisingMetrics]:
        statement = select(AdvertisingMetrics).where(AdvertisingMetrics.date >= start_date, AdvertisingMetrics.date <= end_date).order_by(AdvertisingMetrics.date)
        return list(self.db.execute(statement).scalars().all())
