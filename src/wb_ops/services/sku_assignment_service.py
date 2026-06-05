"""Service layer for multi-operator SKU assignment validation and history tracking."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from wb_ops.db.models import ASSIGNMENT_ROLE_VALUES, AssignmentHistory, Operator, SkuAssignment, SkuPool
from wb_ops.repositories.assignment_repository import AssignmentHistoryRepository, SkuAssignmentRepository
from wb_ops.repositories.operator_repository import OperatorRepository
from wb_ops.repositories.sku_repository import SkuRepository


class AssignmentError(ValueError):
    """Raised when an assignment violates business rules."""


@dataclass(slots=True)
class AssignmentResult:
    """Result of creating or changing a SKU assignment."""

    assignment: SkuAssignment
    history: AssignmentHistory
    created: bool


class SkuAssignmentService:
    """Assign SKUs to multiple responsible operators while preserving history."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.skus = SkuRepository(db)
        self.operators = OperatorRepository(db)
        self.assignments = SkuAssignmentRepository(db)
        self.history = AssignmentHistoryRepository(db)

    def create_operator(self, operator_name: str, status: str = "在职") -> Operator:
        if not operator_name.strip():
            raise AssignmentError("operator_name is required")
        existing = self.operators.get_by_name(operator_name)
        if existing is not None:
            raise AssignmentError(f"Operator already exists: {operator_name}")
        operator = self.operators.create(operator_name=operator_name, status=status)
        self.db.commit()
        return operator

    def create_sku(self, sku: str, product_name: str, category: str | None = None, status: str = "待分配") -> SkuPool:
        if not sku.strip():
            raise AssignmentError("sku is required")
        if not product_name.strip():
            raise AssignmentError("product_name is required")
        existing = self.skus.get_by_sku(sku)
        if existing is not None:
            raise AssignmentError(f"SKU already exists: {sku}")
        sku_item = self.skus.create(sku=sku, product_name=product_name, category=category, status=status)
        self.db.commit()
        return sku_item

    def assign_sku(self, sku_id: int, operator_id: int, *, role: str = "owner") -> AssignmentResult:
        self._validate_role(role)
        sku_item = self._require_sku(sku_id)
        operator = self._require_active_operator(operator_id)
        existing = self.assignments.get_by_sku_operator_role(sku_item.id, operator.id, role)
        if existing is not None:
            raise AssignmentError("Duplicate SKU assignment for operator and role")

        assignment = self.assignments.create(sku_id=sku_item.id, operator_id=operator.id, role=role)
        history = self.history.create(
            sku_id=sku_item.id,
            old_operator_id=None,
            new_operator_id=operator.id,
            role=role,
            action="assigned",
        )
        self._refresh_sku_assignment_state(sku_item)
        self.db.commit()
        return AssignmentResult(assignment=assignment, history=history, created=True)

    def reassign_role(self, sku_id: int, old_operator_id: int, new_operator_id: int, *, role: str = "owner") -> AssignmentResult:
        self._validate_role(role)
        sku_item = self._require_sku(sku_id)
        self._require_operator(old_operator_id)
        new_operator = self._require_active_operator(new_operator_id)
        assignment = self.assignments.get_by_sku_operator_role(sku_item.id, old_operator_id, role)
        if assignment is None:
            raise AssignmentError("Assignment does not exist for SKU, operator, and role")
        duplicate = self.assignments.get_by_sku_operator_role(sku_item.id, new_operator.id, role)
        if duplicate is not None:
            raise AssignmentError("Duplicate SKU assignment for operator and role")

        self.assignments.update_operator(assignment, new_operator.id)
        history = self.history.create(
            sku_id=sku_item.id,
            old_operator_id=old_operator_id,
            new_operator_id=new_operator.id,
            role=role,
            action="reassigned",
        )
        self._refresh_sku_assignment_state(sku_item)
        self.db.commit()
        return AssignmentResult(assignment=assignment, history=history, created=False)

    def unassign_sku(self, sku_id: int, operator_id: int, *, role: str = "owner") -> None:
        self._validate_role(role)
        sku_item = self._require_sku(sku_id)
        self._require_operator(operator_id)
        assignment = self.assignments.get_by_sku_operator_role(sku_item.id, operator_id, role)
        if assignment is None:
            raise AssignmentError("Assignment does not exist for SKU, operator, and role")
        self.assignments.delete(assignment.id)
        self.history.create(
            sku_id=sku_item.id,
            old_operator_id=operator_id,
            new_operator_id=None,
            role=role,
            action="unassigned",
        )
        self._refresh_sku_assignment_state(sku_item)
        self.db.commit()

    def list_sku_assignments(self, sku_id: int, role: str | None = None) -> list[SkuAssignment]:
        self._require_sku(sku_id)
        if role is not None:
            self._validate_role(role)
        return self.assignments.list_by_sku_id(sku_id, role=role)

    def list_operator_skus(self, operator_id: int, role: str | None = None) -> list[SkuAssignment]:
        self._require_operator(operator_id)
        if role is not None:
            self._validate_role(role)
        return self.assignments.list_by_operator_id(operator_id, role=role)

    def list_assignment_history(self, sku_id: int) -> list[AssignmentHistory]:
        self._require_sku(sku_id)
        return self.history.list_by_sku_id(sku_id)

    def _refresh_sku_assignment_state(self, sku_item: SkuPool) -> None:
        assignments = self.assignments.list_by_sku_id(sku_item.id)
        owner_names = [item.operator_item.operator_name for item in assignments if item.role == "owner"]
        sku_item.owner = ", ".join(owner_names) if owner_names else None
        sku_item.status = "已分配" if assignments else "待分配"
        sku_item.assign_status = sku_item.status
        self.db.flush()

    def _validate_role(self, role: str) -> None:
        if role not in ASSIGNMENT_ROLE_VALUES:
            raise AssignmentError(f"Invalid assignment role: {role}")

    def _require_sku(self, sku_id: int) -> SkuPool:
        sku_item = self.skus.get(sku_id)
        if sku_item is None:
            raise AssignmentError(f"SKU does not exist: {sku_id}")
        return sku_item

    def _require_operator(self, operator_id: int) -> Operator:
        operator = self.operators.get(operator_id)
        if operator is None:
            raise AssignmentError(f"Operator does not exist: {operator_id}")
        return operator

    def _require_active_operator(self, operator_id: int) -> Operator:
        operator = self._require_operator(operator_id)
        if operator.status != "在职":
            raise AssignmentError("Cannot assign SKU to an inactive operator")
        return operator
