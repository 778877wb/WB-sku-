"""Unit tests for permission service."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from wb_ops.db.database import Base
from wb_ops.db.models import OperatorRole, Permission, Role, RolePermission
from wb_ops.repositories.operator_repository import OperatorRepository
from wb_ops.services.permission_service import DEFAULT_ROLES, PermissionError, PermissionService


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with TestingSessionLocal() as session:
        yield session


def test_bootstrap_default_roles_and_permissions(db_session: Session) -> None:
    PermissionService(db_session).bootstrap_defaults()

    assert {role.role_name for role in db_session.query(Role).all()} >= set(DEFAULT_ROLES)
    assert db_session.query(Permission).count() > 0
    assert db_session.query(RolePermission).count() > 0


def test_assign_role_to_operator_and_check_permission(db_session: Session) -> None:
    service = PermissionService(db_session)
    service.bootstrap_defaults()
    operator = OperatorRepository(db_session).create("运营A")
    admin = service.roles.get_by_name("admin")
    assert admin is not None

    service.assign_role_to_operator(operator.id, admin.id)

    assert db_session.query(OperatorRole).count() == 1
    assert service.operator_has_permission(operator.id, "settings:manage") is True


def test_duplicate_operator_role_rejected(db_session: Session) -> None:
    service = PermissionService(db_session)
    service.bootstrap_defaults()
    operator = OperatorRepository(db_session).create("运营A")
    viewer = service.roles.get_by_name("viewer")
    assert viewer is not None
    service.assign_role_to_operator(operator.id, viewer.id)

    with pytest.raises(PermissionError, match="already has role"):
        service.assign_role_to_operator(operator.id, viewer.id)


def test_permission_tables_have_required_fields() -> None:
    assert {column.name for column in Role.__table__.columns} >= {"id", "role_name", "created_at"}
    assert {column.name for column in Permission.__table__.columns} >= {"id", "permission_name", "created_at"}
    assert {column.name for column in RolePermission.__table__.columns} >= {"id", "role_id", "permission_id"}
    assert {column.name for column in OperatorRole.__table__.columns} >= {"id", "operator_id", "role_id"}
