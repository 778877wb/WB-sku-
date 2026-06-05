"""CRUD repository for SKU pool records."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from wb_ops.db.models import SkuPool


class SkuRepository:
    """Database operations for the ``sku_pool`` table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, sku: str, product_name: str, category: str | None = None, status: str = "待分配") -> SkuPool:
        sku_item = SkuPool(sku=sku.strip(), product_name=product_name.strip(), category=category, status=status, assign_status=status)
        self.db.add(sku_item)
        self.db.flush()
        return sku_item

    def get(self, sku_id: int) -> SkuPool | None:
        return self.db.get(SkuPool, sku_id)

    def get_by_sku(self, sku: str) -> SkuPool | None:
        statement = select(SkuPool).where(SkuPool.sku == sku.strip())
        return self.db.execute(statement).scalar_one_or_none()

    def list(self, status: str | None = None) -> list[SkuPool]:
        statement = select(SkuPool).order_by(SkuPool.id)
        if status is not None:
            statement = statement.where(SkuPool.status == status)
        return list(self.db.execute(statement).scalars().all())

    def update(
        self,
        sku_id: int,
        *,
        sku: str | None = None,
        product_name: str | None = None,
        category: str | None = None,
        status: str | None = None,
    ) -> SkuPool | None:
        sku_item = self.get(sku_id)
        if sku_item is None:
            return None
        if sku is not None:
            sku_item.sku = sku.strip()
        if product_name is not None:
            sku_item.product_name = product_name.strip()
        if category is not None:
            sku_item.category = category
        if status is not None:
            sku_item.status = status
            sku_item.assign_status = status
        self.db.flush()
        return sku_item

    def delete(self, sku_id: int) -> bool:
        sku_item = self.get(sku_id)
        if sku_item is None:
            return False
        self.db.delete(sku_item)
        self.db.flush()
        return True
