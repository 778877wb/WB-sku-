"""FastAPI dependency injection helpers."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from wb_ops.db.database import SessionLocal
from wb_ops.services.dashboard_service import DashboardService
from wb_ops.services.sku_assignment_service import SkuAssignmentService


def get_db_session() -> Generator[Session, None, None]:
    """Provide a SQLAlchemy session per API request."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_assignment_service(db: Session = Depends(get_db_session)) -> SkuAssignmentService:
    """Build the SKU assignment service for route handlers."""

    return SkuAssignmentService(db)


def get_dashboard_service(db: Session = Depends(get_db_session)) -> DashboardService:
    """Build the dashboard service for route handlers."""

    return DashboardService(db)


def require_permission(x_operator_id: str | None = Header(default=None), x_permission: str | None = Header(default=None)) -> None:
    """Permission middleware foundation.

    Phase 8 only establishes a hook. Future phases can wire this to
    ``PermissionService.operator_has_permission`` and route-level permission
    declarations. For now, callers may pass optional headers and requests are
    allowed through.
    """

    if x_operator_id is not None and not x_operator_id.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Operator-Id must be numeric")
    _ = x_permission
