"""Repositories for SKU assignments and assignment history."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from wb_ops.db.models import AssignmentHistory, SkuAssignment


class SkuAssignmentRepository:
    """CRUD operations for the many-to-many ``sku_assignment`` table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, sku_id: int, operator_id: int, role: str = "owner", assigned_at: datetime | None = None) -> SkuAssignment:
        assignment = SkuAssignment(
            sku_id=sku_id,
            operator_id=operator_id,
            role=role,
            assigned_at=assigned_at or datetime.utcnow(),
        )
        self.db.add(assignment)
        self.db.flush()
        return assignment

    def get(self, assignment_id: int) -> SkuAssignment | None:
        return self.db.get(SkuAssignment, assignment_id)

    def get_by_sku_operator_role(self, sku_id: int, operator_id: int, role: str) -> SkuAssignment | None:
        statement = select(SkuAssignment).where(
            SkuAssignment.sku_id == sku_id,
            SkuAssignment.operator_id == operator_id,
            SkuAssignment.role == role,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def list_by_sku_id(self, sku_id: int, role: str | None = None) -> list[SkuAssignment]:
        statement = select(SkuAssignment).where(SkuAssignment.sku_id == sku_id).order_by(SkuAssignment.role, SkuAssignment.assigned_at)
        if role is not None:
            statement = statement.where(SkuAssignment.role == role)
        return list(self.db.execute(statement).scalars().all())

    def list_by_operator_id(self, operator_id: int, role: str | None = None) -> list[SkuAssignment]:
        statement = select(SkuAssignment).where(SkuAssignment.operator_id == operator_id).order_by(SkuAssignment.assigned_at.desc())
        if role is not None:
            statement = statement.where(SkuAssignment.role == role)
        return list(self.db.execute(statement).scalars().all())

    def update_operator(self, assignment: SkuAssignment, operator_id: int, assigned_at: datetime | None = None) -> SkuAssignment:
        assignment.operator_id = operator_id
        assignment.assigned_at = assigned_at or datetime.utcnow()
        self.db.flush()
        return assignment

    def delete(self, assignment_id: int) -> bool:
        assignment = self.get(assignment_id)
        if assignment is None:
            return False
        self.db.delete(assignment)
        self.db.flush()
        return True


class AssignmentHistoryRepository:
    """CRUD operations for the ``assignment_history`` table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        sku_id: int,
        old_operator_id: int | None,
        new_operator_id: int | None,
        role: str,
        action: str,
        changed_at: datetime | None = None,
    ) -> AssignmentHistory:
        history = AssignmentHistory(
            sku_id=sku_id,
            old_operator_id=old_operator_id,
            new_operator_id=new_operator_id,
            role=role,
            action=action,
            changed_at=changed_at or datetime.utcnow(),
        )
        self.db.add(history)
        self.db.flush()
        return history

    def list_by_sku_id(self, sku_id: int) -> list[AssignmentHistory]:
        statement = select(AssignmentHistory).where(AssignmentHistory.sku_id == sku_id).order_by(AssignmentHistory.changed_at, AssignmentHistory.id)
        return list(self.db.execute(statement).scalars().all())
