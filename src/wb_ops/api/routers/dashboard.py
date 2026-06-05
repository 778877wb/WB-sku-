"""Dashboard API routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from wb_ops.api.dependencies import get_db_session, require_permission
from wb_ops.api.schemas import InventoryStatisticsResponse, OperatorPerformanceResponse, SalesStatisticsResponse, SkuAssignmentStatisticsResponse
from wb_ops.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(require_permission)])


@router.get("/sales", response_model=SalesStatisticsResponse)
def sales_statistics(start_date: date, end_date: date, db: Session = Depends(get_db_session)) -> SalesStatisticsResponse:
    return SalesStatisticsResponse.model_validate(DashboardService(db).sales_statistics(start_date, end_date).to_dict())


@router.get("/operators", response_model=list[OperatorPerformanceResponse])
def operator_statistics(db: Session = Depends(get_db_session)) -> list[OperatorPerformanceResponse]:
    return [OperatorPerformanceResponse.model_validate(item.to_dict()) for item in DashboardService(db).operator_performance()]


@router.get("/assignments", response_model=SkuAssignmentStatisticsResponse)
def assignment_statistics(db: Session = Depends(get_db_session)) -> SkuAssignmentStatisticsResponse:
    return SkuAssignmentStatisticsResponse.model_validate(DashboardService(db).sku_assignment_statistics().to_dict())


@router.get("/inventory", response_model=InventoryStatisticsResponse)
def inventory_statistics(
    metric_date: date,
    low_inventory_threshold: int = 10,
    db: Session = Depends(get_db_session),
) -> InventoryStatisticsResponse:
    stats = DashboardService(db).inventory_statistics(metric_date, low_inventory_threshold=low_inventory_threshold)
    return InventoryStatisticsResponse.model_validate(stats.to_dict())
