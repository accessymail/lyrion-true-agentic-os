"""Tests for workload process identity."""

from __future__ import annotations

import os

import pytest

from lyrion.execution.process_boundary import (
    ProcessIdentity,
    ProcessIdentityError,
)


def test_identity_requires_positive_pid_and_pgid() -> None:
    with pytest.raises(ProcessIdentityError):
        ProcessIdentity(
            execution_id="execution:test",
            pid=0,
            pgid=1,
        )

    with pytest.raises(ProcessIdentityError):
        ProcessIdentity(
            execution_id="execution:test",
            pid=1,
            pgid=0,
        )


def test_identity_requires_execution_id() -> None:
    with pytest.raises(ProcessIdentityError):
        ProcessIdentity(
            execution_id="",
            pid=1,
            pgid=1,
        )


def test_identity_capture_binds_current_process() -> None:
    identity = ProcessIdentity.capture(
        "execution:test:identity",
        os.getpid(),
    )

    assert identity.execution_id == "execution:test:identity"
    assert identity.pid == os.getpid()
    assert identity.pgid > 0


def test_identity_match_is_exact() -> None:
    identity = ProcessIdentity(
        execution_id="execution:test:identity",
        pid=1234,
        pgid=1234,
    )

    assert identity.matches(
        execution_id="execution:test:identity",
        pid=1234,
        pgid=1234,
    )

    assert not identity.matches(
        execution_id="execution:test:other",
        pid=1234,
        pgid=1234,
    )

    assert not identity.matches(
        execution_id="execution:test:identity",
        pid=1235,
        pgid=1234,
    )

    assert not identity.matches(
        execution_id="execution:test:identity",
        pid=1234,
        pgid=1235,
    )
