"""Operator API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from wb_ops.api.dependencies import get_db_session, require_permission
from wb_ops.api.schemas import OperatorCreate, OperatorResponse, OperatorUpdate
from wb_ops.repositories.operator_repository import OperatorRepository
from wb_ops.services.sku_assignment_service import AssignmentError, SkuAssignmentService

router = APIRouter(prefix="/operators", tags=["operators"], dependencies=[Depends(require_permission)])


@router.get("", response_model=list[OperatorResponse])
def list_operators(status_filter: str | None = None, db: Session = Depends(get_db_session)) -> list[OperatorResponse]:
    return [OperatorResponse.model_validate(item) for item in OperatorRepository(db).list(status=status_filter)]


@router.post("", response_model=OperatorResponse, status_code=status.HTTP_201_CREATED)
def create_operator(payload: OperatorCreate, db: Session = Depends(get_db_session)) -> OperatorResponse:
    try:
        operator = SkuAssignmentService(db).create_operator(operator_name=payload.operator_name, status=payload.status)
    except AssignmentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return OperatorResponse.model_validate(operator)


@router.patch("/{operator_id}", response_model=OperatorResponse)
def update_operator(operator_id: int, payload: OperatorUpdate, db: Session = Depends(get_db_session)) -> OperatorResponse:
    operator = OperatorRepository(db).update(operator_id, operator_name=payload.operator_name, status=payload.status)
    if operator is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")
    db.commit()
    return OperatorResponse.model_validate(operator)
