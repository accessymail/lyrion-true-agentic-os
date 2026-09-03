"""Adversarial tests for SQLAlchemy persistence schema models."""

from typing import cast

from sqlalchemy import DateTime, Integer, String, Table

from lyrion.persistence.sqlalchemy.base import Base
from lyrion.persistence.sqlalchemy.models import (
    PersistentExecutionModel,
    PersistentIdempotencyModel,
    PersistentOpportunityModel,
    RecoveryDecisionModel,
    RuntimeInstanceModel,
    RuntimeLeaseModel,
)


def test_all_persistence_models_share_base() -> None:
    """Every durable model must use the project declarative base."""
    models = (
        RuntimeInstanceModel,
        RuntimeLeaseModel,
        PersistentOpportunityModel,
        PersistentExecutionModel,
        PersistentIdempotencyModel,
        RecoveryDecisionModel,
    )

    for model in models:
        assert model.metadata is Base.metadata


def test_expected_table_names_exist() -> None:
    """The durable schema must expose explicit table names."""
    expected = {
        "runtime_instances",
        "runtime_leases",
        "persistent_opportunities",
        "persistent_executions",
        "persistent_scheduler",
        "idempotency_records",
        "recovery_decisions",
        "voice_identity_profiles",
    }

    assert expected == set(
        Base.metadata.tables,
    )


def test_runtime_instance_has_revision() -> None:
    """Runtime state needs optimistic-concurrency revisioning."""
    column = RuntimeInstanceModel.__table__.c.revision

    assert isinstance(column.type, Integer)
    assert column.nullable is False


def test_lease_has_unique_resource_constraint() -> None:
    """One resource may have only one current durable lease."""
    table = cast(
        Table,
        RuntimeLeaseModel.__table__,
    )

    constraints = {
        constraint.name
        for constraint in table.constraints
        if constraint.name is not None
    }

    assert "uq_runtime_leases_resource_id" in constraints


def test_lease_has_resource_and_expiry_indexes() -> None:
    """Lease lookup and recovery need indexed ownership/expiry fields."""
    table = Base.metadata.tables["runtime_leases"]
    names = {
        index.name
        for index in table.indexes
    }

    assert "ix_runtime_leases_resource_id" in names
    assert "ix_runtime_leases_expires_at" in names


def test_execution_has_revision_and_identity_fields() -> None:
    """Durable execution must retain core identity and concurrency state."""
    table = PersistentExecutionModel.__table__

    assert table.c.execution_id.primary_key is True
    assert table.c.request_id.nullable is False
    assert table.c.opportunity_id.nullable is False
    assert table.c.task_id.nullable is False
    assert table.c.idempotency_key.nullable is False
    assert table.c.revision.nullable is False


def test_idempotency_key_is_unique() -> None:
    """Only one durable reservation may exist for a key."""
    table = Base.metadata.tables["idempotency_records"]

    assert table.c.idempotency_key.primary_key is True

    constraints = {
        constraint.name
        for constraint in table.constraints
        if constraint.name is not None
    }

    assert "uq_idempotency_records_key" in constraints


def test_lifecycle_timestamps_use_timezone_capable_sql_types() -> None:
    """Durable lifecycle timestamps must request timezone support."""
    checks = (
        RuntimeInstanceModel.__table__.c.started_at,
        RuntimeLeaseModel.__table__.c.expires_at,
        PersistentOpportunityModel.__table__.c.created_at,
        PersistentExecutionModel.__table__.c.created_at,
        PersistentIdempotencyModel.__table__.c.reserved_at,
        RecoveryDecisionModel.__table__.c.evaluated_at,
    )

    for column in checks:
        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True


def test_string_identity_columns_are_bounded() -> None:
    """Persisted identifiers should retain domain size boundaries."""
    checks = (
        RuntimeInstanceModel.__table__.c.instance_id,
        PersistentExecutionModel.__table__.c.execution_id,
        PersistentExecutionModel.__table__.c.request_id,
        PersistentIdempotencyModel.__table__.c.idempotency_key,
    )

    for column in checks:
        assert isinstance(column.type, String)
        assert column.type.length in {200, 500}
