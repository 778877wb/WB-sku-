"""Repositories for roles and permissions."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from wb_ops.db.models import OperatorRole, Permission, Role, RolePermission


class RoleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_name(self, role_name: str) -> Role | None:
        return self.db.execute(select(Role).where(Role.role_name == role_name)).scalar_one_or_none()

    def create(self, role_name: str, description: str | None = None) -> Role:
        role = Role(role_name=role_name, description=description)
        self.db.add(role)
        self.db.flush()
        return role

    def get_or_create(self, role_name: str, description: str | None = None) -> Role:
        return self.get_by_name(role_name) or self.create(role_name, description)


class PermissionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_name(self, permission_name: str) -> Permission | None:
        return self.db.execute(select(Permission).where(Permission.permission_name == permission_name)).scalar_one_or_none()

    def create(self, permission_name: str, description: str | None = None) -> Permission:
        permission = Permission(permission_name=permission_name, description=description)
        self.db.add(permission)
        self.db.flush()
        return permission

    def get_or_create(self, permission_name: str, description: str | None = None) -> Permission:
        return self.get_by_name(permission_name) or self.create(permission_name, description)


class RolePermissionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def exists(self, role_id: int, permission_id: int) -> bool:
        statement = select(RolePermission).where(RolePermission.role_id == role_id, RolePermission.permission_id == permission_id)
        return self.db.execute(statement).scalar_one_or_none() is not None

    def create(self, role_id: int, permission_id: int) -> RolePermission:
        mapping = RolePermission(role_id=role_id, permission_id=permission_id)
        self.db.add(mapping)
        self.db.flush()
        return mapping


class OperatorRoleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def exists(self, operator_id: int, role_id: int) -> bool:
        statement = select(OperatorRole).where(OperatorRole.operator_id == operator_id, OperatorRole.role_id == role_id)
        return self.db.execute(statement).scalar_one_or_none() is not None

    def create(self, operator_id: int, role_id: int) -> OperatorRole:
        mapping = OperatorRole(operator_id=operator_id, role_id=role_id)
        self.db.add(mapping)
        self.db.flush()
        return mapping

    def list_roles_for_operator(self, operator_id: int) -> list[Role]:
        statement = select(Role).join(OperatorRole, OperatorRole.role_id == Role.id).where(OperatorRole.operator_id == operator_id)
        return list(self.db.execute(statement).scalars().all())
