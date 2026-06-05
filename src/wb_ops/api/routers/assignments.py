"""Assignment API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from wb_ops.api.dependencies import get_db_session, require_permission
from wb_ops.api.schemas import AssignmentCreate, AssignmentDelete, AssignmentHistoryResponse, AssignmentResponse
from wb_ops.services.sku_assignment_service import AssignmentError, SkuAssignmentService

router = APIRouter(prefix="/assignments", tags=["assignments"], dependencies=[Depends(require_permission)])


@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_operator_to_sku(payload: AssignmentCreate, db: Session = Depends(get_db_session)) -> AssignmentResponse:
    try:
        result = SkuAssignmentService(db).assign_sku(payload.sku_id, payload.operator_id, role=payload.role)
    except AssignmentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AssignmentResponse.model_validate(result.assignment)


@router.delete("/skus/{sku_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_assignment(sku_id: int, payload: AssignmentDelete, db: Session = Depends(get_db_session)) -> Response:
    try:
        SkuAssignmentService(db).unassign_sku(sku_id, payload.operator_id, role=payload.role)
    except AssignmentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/skus/{sku_id}/history", response_model=list[AssignmentHistoryResponse])
def assignment_history(sku_id: int, db: Session = Depends(get_db_session)) -> list[AssignmentHistoryResponse]:
    try:
        history = SkuAssignmentService(db).list_assignment_history(sku_id)
    except AssignmentError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [AssignmentHistoryResponse.model_validate(item) for item in history]
