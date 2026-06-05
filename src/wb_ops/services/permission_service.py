"""Permission service for roles, permissions, and operator-role mappings."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from wb_ops.db.models import Permission, Role, RolePermission
from wb_ops.repositories.operator_repository import OperatorRepository
from wb_ops.repositories.permission_repository import OperatorRoleRepository, PermissionRepository, RolePermissionRepository, RoleRepository

DEFAULT_ROLES = ("admin", "manager", "operator", "viewer")
DEFAULT_PERMISSIONS = (
    "sku:read",
    "sku:write",
    "assignment:manage",
    "metrics:read",
    "reports:read",
    "settings:manage",
)
DEFAULT_ROLE_PERMISSIONS = {
    "admin": DEFAULT_PERMISSIONS,
    "manager": ("sku:read", "sku:write", "assignment:manage", "metrics:read", "reports:read"),
    "operator": ("sku:read", "sku:write", "metrics:read"),
    "viewer": ("sku:read", "metrics:read", "reports:read"),
}


class PermissionError(ValueError):
    """Raised for permission system validation errors."""


class PermissionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.roles = RoleRepository(db)
        self.permissions = PermissionRepository(db)
        self.role_permissions = RolePermissionRepository(db)
        self.operator_roles = OperatorRoleRepository(db)
        self.operators = OperatorRepository(db)

    def bootstrap_defaults(self) -> None:
        for role_name in DEFAULT_ROLES:
            self.roles.get_or_create(role_name)
        for permission_name in DEFAULT_PERMISSIONS:
            self.permissions.get_or_create(permission_name)
        for role_name, permission_names in DEFAULT_ROLE_PERMISSIONS.items():
            role = self.roles.get_by_name(role_name)
            if role is None:
                raise PermissionError(f"Role missing after bootstrap: {role_name}")
            for permission_name in permission_names:
                permission = self.permissions.get_by_name(permission_name)
                if permission is None:
                    raise PermissionError(f"Permission missing after bootstrap: {permission_name}")
                self.grant_permission_to_role(role.id, permission.id)
        self.db.commit()

    def grant_permission_to_role(self, role_id: int, permission_id: int) -> RolePermission:
        if self.db.get(Role, role_id) is None:
            raise PermissionError(f"Role does not exist: {role_id}")
        if self.db.get(Permission, permission_id) is None:
            raise PermissionError(f"Permission does not exist: {permission_id}")
        if self.role_permissions.exists(role_id, permission_id):
            raise PermissionError("Role already has permission")
        mapping = self.role_permissions.create(role_id, permission_id)
        self.db.flush()
        return mapping

    def assign_role_to_operator(self, operator_id: int, role_id: int) -> None:
        if self.operators.get(operator_id) is None:
            raise PermissionError(f"Operator does not exist: {operator_id}")
        if self.db.get(Role, role_id) is None:
            raise PermissionError(f"Role does not exist: {role_id}")
        if self.operator_roles.exists(operator_id, role_id):
            raise PermissionError("Operator already has role")
        self.operator_roles.create(operator_id, role_id)
        self.db.commit()

    def operator_has_permission(self, operator_id: int, permission_name: str) -> bool:
        statement = (
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .where(Permission.permission_name == permission_name)
        )
        role_ids = {role.id for role in self.operator_roles.list_roles_for_operator(operator_id)}
        return any(permission for permission in self.db.execute(statement.where(Role.id.in_(role_ids))).scalars().all())
