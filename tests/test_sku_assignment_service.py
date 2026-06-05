"""Unit tests for multi-operator SKU assignment business rules."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from wb_ops.db.database import Base
from wb_ops.db.models import AssignmentHistory, Operator, SkuAssignment, SkuPool
from wb_ops.services.sku_assignment_service import AssignmentError, SkuAssignmentService


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with TestingSessionLocal() as session:
        yield session


def test_create_operator_and_sku(db_session: Session) -> None:
    service = SkuAssignmentService(db_session)

    operator = service.create_operator("运营A")
    sku = service.create_sku("SKU-001", "Test product", "Beauty")

    assert operator.id is not None
    assert operator.operator_name == "运营A"
    assert sku.id is not None
    assert sku.sku == "SKU-001"
    assert sku.status == "待分配"


def test_sku_can_have_multiple_operators_with_roles(db_session: Session) -> None:
    service = SkuAssignmentService(db_session)
    owner = service.create_operator("运营A")
    assistant = service.create_operator("运营B")
    advertiser = service.create_operator("运营C")
    sku = service.create_sku("SKU-001", "Test product", "Beauty")

    service.assign_sku(sku.id, owner.id, role="owner")
    service.assign_sku(sku.id, assistant.id, role="assistant")
    service.assign_sku(sku.id, advertiser.id, role="advertising")

    assignments = service.list_sku_assignments(sku.id)
    assert {(item.operator_id, item.role) for item in assignments} == {
        (owner.id, "owner"),
        (assistant.id, "assistant"),
        (advertiser.id, "advertising"),
    }
    assert sku.owner == "运营A"
    assert sku.status == "已分配"


def test_duplicate_assignment_same_sku_operator_role_is_rejected(db_session: Session) -> None:
    service = SkuAssignmentService(db_session)
    operator = service.create_operator("运营A")
    sku = service.create_sku("SKU-001", "Test product", "Beauty")

    service.assign_sku(sku.id, operator.id, role="owner")

    with pytest.raises(AssignmentError, match="Duplicate SKU assignment"):
        service.assign_sku(sku.id, operator.id, role="owner")

    assignments = db_session.query(SkuAssignment).filter_by(sku_id=sku.id).all()
    assert len(assignments) == 1


def test_same_operator_can_have_multiple_roles_on_same_sku(db_session: Session) -> None:
    service = SkuAssignmentService(db_session)
    operator = service.create_operator("运营A")
    sku = service.create_sku("SKU-001", "Test product", "Beauty")

    service.assign_sku(sku.id, operator.id, role="owner")
    service.assign_sku(sku.id, operator.id, role="advertising")

    assignments = service.list_sku_assignments(sku.id)
    assert {(item.operator_id, item.role) for item in assignments} == {(operator.id, "owner"), (operator.id, "advertising")}


def test_reassignment_updates_assignment_and_history(db_session: Session) -> None:
    service = SkuAssignmentService(db_session)
    operator_a = service.create_operator("运营A")
    operator_b = service.create_operator("运营B")
    sku = service.create_sku("SKU-001", "Test product", "Beauty")

    service.assign_sku(sku.id, operator_a.id, role="owner")
    second_result = service.reassign_role(sku.id, operator_a.id, operator_b.id, role="owner")

    assert second_result.created is False
    assert second_result.assignment.operator_id == operator_b.id
    assert second_result.history.old_operator_id == operator_a.id
    assert second_result.history.new_operator_id == operator_b.id
    assert second_result.history.role == "owner"
    assert second_result.history.action == "reassigned"
    assert sku.owner == "运营B"

    histories = db_session.query(AssignmentHistory).filter_by(sku_id=sku.id).order_by(AssignmentHistory.id).all()
    assert [(item.old_operator_id, item.new_operator_id, item.role, item.action) for item in histories] == [
        (None, operator_a.id, "owner", "assigned"),
        (operator_a.id, operator_b.id, "owner", "reassigned"),
    ]


def test_unassign_writes_history_and_refreshes_state(db_session: Session) -> None:
    service = SkuAssignmentService(db_session)
    operator = service.create_operator("运营A")
    sku = service.create_sku("SKU-001", "Test product", "Beauty")

    service.assign_sku(sku.id, operator.id, role="owner")
    service.unassign_sku(sku.id, operator.id, role="owner")

    assert service.list_sku_assignments(sku.id) == []
    assert sku.owner is None
    assert sku.status == "待分配"
    history = service.list_assignment_history(sku.id)[-1]
    assert history.old_operator_id == operator.id
    assert history.new_operator_id is None
    assert history.action == "unassigned"


def test_duplicate_sku_and_operator_are_rejected(db_session: Session) -> None:
    service = SkuAssignmentService(db_session)
    service.create_operator("运营A")
    service.create_sku("SKU-001", "Test product", "Beauty")

    with pytest.raises(AssignmentError, match="Operator already exists"):
        service.create_operator("运营A")
    with pytest.raises(AssignmentError, match="SKU already exists"):
        service.create_sku("SKU-001", "Another product", "Beauty")


def test_inactive_operator_cannot_receive_assignment(db_session: Session) -> None:
    service = SkuAssignmentService(db_session)
    operator = service.create_operator("运营A", status="离职")
    sku = service.create_sku("SKU-001", "Test product", "Beauty")

    with pytest.raises(AssignmentError, match="inactive operator"):
        service.assign_sku(sku.id, operator.id, role="owner")


def test_operator_can_manage_multiple_skus(db_session: Session) -> None:
    service = SkuAssignmentService(db_session)
    operator = service.create_operator("运营A")
    sku_1 = service.create_sku("SKU-001", "Product 1", "Beauty")
    sku_2 = service.create_sku("SKU-002", "Product 2", "Beauty")

    service.assign_sku(sku_1.id, operator.id, role="owner")
    service.assign_sku(sku_2.id, operator.id, role="owner")

    assignments = service.list_operator_skus(operator.id)
    assert {assignment.sku_id for assignment in assignments} == {sku_1.id, sku_2.id}


def test_invalid_role_is_rejected(db_session: Session) -> None:
    service = SkuAssignmentService(db_session)
    operator = service.create_operator("运营A")
    sku = service.create_sku("SKU-001", "Test product", "Beauty")

    with pytest.raises(AssignmentError, match="Invalid assignment role"):
        service.assign_sku(sku.id, operator.id, role="bad_role")


def test_assignment_tables_have_required_field_names() -> None:
    assert {column.name for column in Operator.__table__.columns} >= {"id", "operator_name", "status", "created_at"}
    assert {column.name for column in SkuPool.__table__.columns} >= {"id", "sku", "product_name", "category", "status", "created_at"}
    assert {column.name for column in SkuAssignment.__table__.columns} >= {"id", "sku_id", "operator_id", "role", "assigned_at"}
    assert {column.name for column in AssignmentHistory.__table__.columns} >= {
        "id",
        "sku_id",
        "old_operator_id",
        "new_operator_id",
        "role",
        "action",
        "changed_at",
    }
