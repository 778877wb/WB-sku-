"""SQLAlchemy ORM models for Phase 1 of the WB operations management system."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from wb_ops.db.database import Base

ASSIGN_STATUS_VALUES = ("待分配", "已分配", "已完成", "暂停")
LISTING_STATUS_VALUES = ("未上架", "已上架")
OPERATOR_STATUS_VALUES = ("在职", "离职")
ASSIGNMENT_STATUS_VALUES = ("待上架", "已上架", "已优化", "完成")
ASSIGNMENT_ROLE_VALUES = ("owner", "assistant", "advertising", "inventory", "customer_service")
SKU_STATUS_VALUES = ("待分配", "已分配", "已完成", "暂停")
WB_LISTING_STATUS_VALUES = ("已上架", "已下架")
OPTIMIZE_TYPE_VALUES = ("标题优化", "主图优化", "详情优化", "价格优化", "广告优化", "评价维护")


def _in_check(column_name: str, values: tuple[str, ...]) -> str:
    """Build a portable SQL CHECK expression for fixed Chinese enum values."""

    quoted_values = ", ".join(f"'{value}'" for value in values)
    return f"{column_name} in ({quoted_values})"


class TimestampMixin:
    """Common created/updated timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SkuPool(TimestampMixin, Base):
    """SKU master pool.

    ``sku`` is globally unique. A SKU can be listed in multiple WB shops, so
    shop-specific listing rows live in ``wb_listing``.
    """

    __tablename__ = "sku_pool"
    __table_args__ = (
        CheckConstraint(_in_check("assign_status", ASSIGN_STATUS_VALUES), name="ck_sku_pool_assign_status"),
        CheckConstraint(_in_check("listing_status", LISTING_STATUS_VALUES), name="ck_sku_pool_listing_status"),
        CheckConstraint(_in_check("status", SKU_STATUS_VALUES), name="ck_sku_pool_status"),
        CheckConstraint("warehouse_stock >= 0", name="ck_sku_pool_warehouse_stock_non_negative"),
        CheckConstraint("shop_count >= 0", name="ck_sku_pool_shop_count_non_negative"),
        CheckConstraint("sales_30d >= 0", name="ck_sku_pool_sales_30d_non_negative"),
        CheckConstraint("review_count >= 0", name="ck_sku_pool_review_count_non_negative"),
        CheckConstraint("question_count >= 0", name="ck_sku_pool_question_count_non_negative"),
        CheckConstraint("rating >= 0 and rating <= 5", name="ck_sku_pool_rating_range"),
        Index("ix_sku_pool_assign_listing", "assign_status", "listing_status"),
        Index("ix_sku_pool_brand_category", "brand", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(128), index=True)
    category: Mapped[str | None] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="待分配", index=True, nullable=False)
    warehouse_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    arrival_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    owner: Mapped[str | None] = mapped_column(String(128), index=True)
    assign_status: Mapped[str] = mapped_column(String(32), default="待分配", index=True, nullable=False)
    listing_status: Mapped[str] = mapped_column(String(32), default="未上架", index=True, nullable=False)
    shop_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sales_30d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.00"), nullable=False)
    needs_optimization: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    assignments: Mapped[list["SkuAssignment"]] = relationship(back_populates="sku_item", cascade="all, delete-orphan")
    assignment_history: Mapped[list["AssignmentHistory"]] = relationship(back_populates="sku_item", cascade="all, delete-orphan")
    listings: Mapped[list["WbListing"]] = relationship(back_populates="sku_item", cascade="all, delete-orphan")
    optimization_records: Mapped[list["OptimizationRecord"]] = relationship(back_populates="sku_item", cascade="all, delete-orphan")
    metrics: Mapped[list["WbMetrics"]] = relationship(back_populates="sku_item", cascade="all, delete-orphan")


class Operator(Base):
    """Operation team member."""

    __tablename__ = "operators"
    __table_args__ = (CheckConstraint(_in_check("status", OPERATOR_STATUS_VALUES), name="ck_operators_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operator_name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    name = synonym("operator_name")
    status: Mapped[str] = mapped_column(String(32), default="在职", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    assignments: Mapped[list["SkuAssignment"]] = relationship(back_populates="operator_item")
    old_assignment_history: Mapped[list["AssignmentHistory"]] = relationship(
        back_populates="old_operator", foreign_keys="AssignmentHistory.old_operator_id"
    )
    new_assignment_history: Mapped[list["AssignmentHistory"]] = relationship(
        back_populates="new_operator", foreign_keys="AssignmentHistory.new_operator_id"
    )


class SkuAssignment(Base):
    """Current many-to-many responsibility assignment for SKU and operator.

    A SKU can have multiple responsible operators. Duplicate assignments are
    prevented by the unique ``sku_id + operator_id + role`` constraint.
    """

    __tablename__ = "sku_assignment"
    __table_args__ = (
        CheckConstraint(_in_check("role", ASSIGNMENT_ROLE_VALUES), name="ck_sku_assignment_role"),
        UniqueConstraint("sku_id", "operator_id", "role", name="uq_sku_assignment_sku_operator_role"),
        Index("ix_sku_assignment_sku_role", "sku_id", "role"),
        Index("ix_sku_assignment_operator_assigned", "operator_id", "assigned_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku_id: Mapped[int] = mapped_column(Integer, ForeignKey("sku_pool.id", ondelete="CASCADE"), index=True, nullable=False)
    operator_id: Mapped[int] = mapped_column(Integer, ForeignKey("operators.id", ondelete="RESTRICT"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="owner", index=True, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True, nullable=False)

    sku_item: Mapped[SkuPool] = relationship(back_populates="assignments")
    operator_item: Mapped[Operator] = relationship(back_populates="assignments")


class AssignmentHistory(Base):
    """History of assignment changes for audit and performance tracking."""

    __tablename__ = "assignment_history"
    __table_args__ = (
        CheckConstraint(_in_check("role", ASSIGNMENT_ROLE_VALUES), name="ck_assignment_history_role"),
        CheckConstraint("action in ('assigned', 'reassigned', 'unassigned')", name="ck_assignment_history_action"),
        Index("ix_assignment_history_sku_changed", "sku_id", "changed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku_id: Mapped[int] = mapped_column(Integer, ForeignKey("sku_pool.id", ondelete="CASCADE"), index=True, nullable=False)
    old_operator_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("operators.id", ondelete="SET NULL"), index=True)
    new_operator_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("operators.id", ondelete="SET NULL"), index=True)
    role: Mapped[str] = mapped_column(String(32), default="owner", index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(32), default="assigned", index=True, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True, nullable=False)

    sku_item: Mapped[SkuPool] = relationship(back_populates="assignment_history")
    old_operator: Mapped[Operator | None] = relationship(
        back_populates="old_assignment_history", foreign_keys=[old_operator_id]
    )
    new_operator: Mapped[Operator | None] = relationship(
        back_populates="new_assignment_history", foreign_keys=[new_operator_id]
    )

class WbListing(Base):
    """WB shop listing record.

    A single SKU may have multiple rows here because it can be listed in
    multiple Wildberries shops.
    """

    __tablename__ = "wb_listing"
    __table_args__ = (
        CheckConstraint(_in_check("status", WB_LISTING_STATUS_VALUES), name="ck_wb_listing_status"),
        UniqueConstraint("shop_name", "nm_id", name="uq_wb_listing_shop_nm_id"),
        UniqueConstraint("shop_name", "vendor_code", name="uq_wb_listing_shop_vendor_code"),
        Index("ix_wb_listing_sku_shop", "sku", "shop_name"),
        Index("ix_wb_listing_status_sync", "status", "last_sync_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(128), ForeignKey("sku_pool.sku", ondelete="CASCADE"), index=True, nullable=False)
    shop_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    nm_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    vendor_code: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    listing_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="已上架", index=True, nullable=False)
    last_sync_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    sku_item: Mapped[SkuPool] = relationship(back_populates="listings")


class OptimizationRecord(Base):
    """SKU optimization action record."""

    __tablename__ = "optimization_record"
    __table_args__ = (
        CheckConstraint(_in_check("optimize_type", OPTIMIZE_TYPE_VALUES), name="ck_optimization_record_type"),
        Index("ix_optimization_record_operator_time", "operator", "optimize_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(128), ForeignKey("sku_pool.sku", ondelete="CASCADE"), index=True, nullable=False)
    operator: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    optimize_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True, nullable=False)
    optimize_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)

    sku_item: Mapped[SkuPool] = relationship(back_populates="optimization_records")


class WbMetrics(Base):
    """Daily WB operational metrics by SKU and shop."""

    __tablename__ = "wb_metrics"
    __table_args__ = (
        UniqueConstraint("sku", "shop_name", "date", name="uq_wb_metrics_sku_shop_date"),
        CheckConstraint("sales_qty >= 0", name="ck_wb_metrics_sales_qty_non_negative"),
        CheckConstraint("sales_amount >= 0", name="ck_wb_metrics_sales_amount_non_negative"),
        CheckConstraint("stock >= 0", name="ck_wb_metrics_stock_non_negative"),
        CheckConstraint("review_count >= 0", name="ck_wb_metrics_review_count_non_negative"),
        CheckConstraint("question_count >= 0", name="ck_wb_metrics_question_count_non_negative"),
        CheckConstraint("rating >= 0 and rating <= 5", name="ck_wb_metrics_rating_range"),
        Index("ix_wb_metrics_date_sales", "date", "sales_qty"),
        Index("ix_wb_metrics_sku_date", "sku", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(128), ForeignKey("sku_pool.sku", ondelete="CASCADE"), index=True, nullable=False)
    shop_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    sales_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sales_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.00"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sku_item: Mapped[SkuPool] = relationship(back_populates="metrics")


class DailyMetrics(Base):
    """Daily SKU sales, revenue, order, and return metrics."""

    __tablename__ = "daily_metrics"
    __table_args__ = (
        UniqueConstraint("sku_id", "date", name="uq_daily_metrics_sku_date"),
        CheckConstraint("sales >= 0", name="ck_daily_metrics_sales_non_negative"),
        CheckConstraint("revenue >= 0", name="ck_daily_metrics_revenue_non_negative"),
        CheckConstraint("orders >= 0", name="ck_daily_metrics_orders_non_negative"),
        CheckConstraint("returns >= 0", name="ck_daily_metrics_returns_non_negative"),
        Index("ix_daily_metrics_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku_id: Mapped[int] = mapped_column(Integer, ForeignKey("sku_pool.id", ondelete="CASCADE"), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    sales: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    returns: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class InventoryMetrics(Base):
    """Daily SKU inventory quantity metrics."""

    __tablename__ = "inventory_metrics"
    __table_args__ = (
        UniqueConstraint("sku_id", "date", name="uq_inventory_metrics_sku_date"),
        CheckConstraint("inventory_quantity >= 0", name="ck_inventory_metrics_quantity_non_negative"),
        Index("ix_inventory_metrics_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku_id: Mapped[int] = mapped_column(Integer, ForeignKey("sku_pool.id", ondelete="CASCADE"), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    inventory_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AdvertisingMetrics(Base):
    """Daily SKU advertising spend and efficiency metrics."""

    __tablename__ = "advertising_metrics"
    __table_args__ = (
        UniqueConstraint("sku_id", "date", name="uq_advertising_metrics_sku_date"),
        CheckConstraint("ad_spend >= 0", name="ck_advertising_metrics_spend_non_negative"),
        CheckConstraint("ctr >= 0", name="ck_advertising_metrics_ctr_non_negative"),
        CheckConstraint("cpc >= 0", name="ck_advertising_metrics_cpc_non_negative"),
        Index("ix_advertising_metrics_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku_id: Mapped[int] = mapped_column(Integer, ForeignKey("sku_pool.id", ondelete="CASCADE"), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    ad_spend: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    ctr: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0.0000"), nullable=False)
    cpc: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0.0000"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Role(Base):
    """Permission role such as admin, manager, operator, or viewer."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    permissions: Mapped[list["RolePermission"]] = relationship(back_populates="role", cascade="all, delete-orphan")
    operators: Mapped[list["OperatorRole"]] = relationship(back_populates="role", cascade="all, delete-orphan")


class Permission(Base):
    """Atomic permission granted to roles."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    permission_name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    roles: Mapped[list["RolePermission"]] = relationship(back_populates="permission", cascade="all, delete-orphan")


class RolePermission(Base):
    """Many-to-many role to permission mapping."""

    __tablename__ = "role_permission"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission_role_permission"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), index=True, nullable=False)
    permission_id: Mapped[int] = mapped_column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    role: Mapped[Role] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship(back_populates="roles")


class OperatorRole(Base):
    """Many-to-many operator to role mapping."""

    __tablename__ = "operator_role"
    __table_args__ = (UniqueConstraint("operator_id", "role_id", name="uq_operator_role_operator_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operator_id: Mapped[int] = mapped_column(Integer, ForeignKey("operators.id", ondelete="CASCADE"), index=True, nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    operator: Mapped[Operator] = relationship()
    role: Mapped[Role] = relationship(back_populates="operators")
