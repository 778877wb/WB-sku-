"""CRUD repository for operators."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from wb_ops.db.models import Operator


class OperatorRepository:
    """Database operations for the ``operators`` table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, operator_name: str, status: str = "在职") -> Operator:
        operator = Operator(operator_name=operator_name.strip(), status=status)
        self.db.add(operator)
        self.db.flush()
        return operator

    def get(self, operator_id: int) -> Operator | None:
        return self.db.get(Operator, operator_id)

    def get_by_name(self, operator_name: str) -> Operator | None:
        statement = select(Operator).where(Operator.operator_name == operator_name.strip())
        return self.db.execute(statement).scalar_one_or_none()

    def list(self, status: str | None = None) -> list[Operator]:
        statement = select(Operator).order_by(Operator.id)
        if status is not None:
            statement = statement.where(Operator.status == status)
        return list(self.db.execute(statement).scalars().all())

    def update(self, operator_id: int, *, operator_name: str | None = None, status: str | None = None) -> Operator | None:
        operator = self.get(operator_id)
        if operator is None:
            return None
        if operator_name is not None:
            operator.operator_name = operator_name.strip()
        if status is not None:
            operator.status = status
        self.db.flush()
        return operator

    def delete(self, operator_id: int) -> bool:
        operator = self.get(operator_id)
        if operator is None:
            return False
        self.db.delete(operator)
        self.db.flush()
        return True
