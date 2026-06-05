"""Service layer for SKU metrics ingestion and validation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from wb_ops.db.models import AdvertisingMetrics, DailyMetrics, InventoryMetrics
from wb_ops.repositories.metrics_repository import AdvertisingMetricsRepository, DailyMetricsRepository, InventoryMetricsRepository
from wb_ops.repositories.sku_repository import SkuRepository


class MetricsError(ValueError):
    """Raised when metrics data is invalid."""


class MetricsService:
    """Validate and upsert daily, inventory, and advertising metrics."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.skus = SkuRepository(db)
        self.daily = DailyMetricsRepository(db)
        self.inventory = InventoryMetricsRepository(db)
        self.advertising = AdvertisingMetricsRepository(db)

    def record_daily_metrics(self, *, sku_id: int, metric_date: date, sales: int, revenue: Decimal, orders: int, returns: int) -> DailyMetrics:
        self._require_sku(sku_id)
        self._validate_non_negative(sales=sales, revenue=revenue, orders=orders, returns=returns)
        record = self.daily.upsert(sku_id=sku_id, metric_date=metric_date, sales=sales, revenue=revenue, orders=orders, returns=returns)
        self.db.commit()
        return record

    def record_inventory_metrics(self, *, sku_id: int, metric_date: date, inventory_quantity: int) -> InventoryMetrics:
        self._require_sku(sku_id)
        self._validate_non_negative(inventory_quantity=inventory_quantity)
        record = self.inventory.upsert(sku_id=sku_id, metric_date=metric_date, inventory_quantity=inventory_quantity)
        self.db.commit()
        return record

    def record_advertising_metrics(self, *, sku_id: int, metric_date: date, ad_spend: Decimal, ctr: Decimal, cpc: Decimal) -> AdvertisingMetrics:
        self._require_sku(sku_id)
        self._validate_non_negative(ad_spend=ad_spend, ctr=ctr, cpc=cpc)
        record = self.advertising.upsert(sku_id=sku_id, metric_date=metric_date, ad_spend=ad_spend, ctr=ctr, cpc=cpc)
        self.db.commit()
        return record

    def _require_sku(self, sku_id: int) -> None:
        if self.skus.get(sku_id) is None:
            raise MetricsError(f"SKU does not exist: {sku_id}")

    def _validate_non_negative(self, **values: int | Decimal) -> None:
        for name, value in values.items():
            if value < 0:
                raise MetricsError(f"{name} must be non-negative")
