"""SKU API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from wb_ops.api.dependencies import get_db_session, require_permission
from wb_ops.api.schemas import SkuCreate, SkuResponse, SkuUpdate
from wb_ops.repositories.sku_repository import SkuRepository
from wb_ops.services.sku_assignment_service import AssignmentError, SkuAssignmentService

router = APIRouter(prefix="/skus", tags=["skus"], dependencies=[Depends(require_permission)])


@router.get("", response_model=list[SkuResponse])
def list_skus(status_filter: str | None = None, db: Session = Depends(get_db_session)) -> list[SkuResponse]:
    return [SkuResponse.model_validate(item) for item in SkuRepository(db).list(status=status_filter)]


@router.post("", response_model=SkuResponse, status_code=status.HTTP_201_CREATED)
def create_sku(payload: SkuCreate, db: Session = Depends(get_db_session)) -> SkuResponse:
    try:
        sku = SkuAssignmentService(db).create_sku(
            sku=payload.sku,
            product_name=payload.product_name,
            category=payload.category,
            status=payload.status,
        )
    except AssignmentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SkuResponse.model_validate(sku)


@router.patch("/{sku_id}", response_model=SkuResponse)
def update_sku(sku_id: int, payload: SkuUpdate, db: Session = Depends(get_db_session)) -> SkuResponse:
    sku = SkuRepository(db).update(
        sku_id,
        sku=payload.sku,
        product_name=payload.product_name,
        category=payload.category,
        status=payload.status,
    )
    if sku is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SKU not found")
    db.commit()
    return SkuResponse.model_validate(sku)


@router.delete("/{sku_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sku(sku_id: int, db: Session = Depends(get_db_session)) -> Response:
    deleted = SkuRepository(db).delete(sku_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SKU not found")
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
