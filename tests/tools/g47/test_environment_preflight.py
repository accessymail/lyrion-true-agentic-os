from __future__ import annotations

import json
from pathlib import Path

import pytest
from tools.g47.environment_preflight import (
    build_inventory,
    collect_environment_metadata,
    prepare_workspace,
)


def test_metadata_is_non_certifying() -> None:
    metadata = collect_environment_metadata()

    certification = metadata["certification"]

    assert isinstance(certification, dict)
    assert certification["production_certified"] is False


def test_workspace_contains_metadata_and_inventory(tmp_path: Path) -> None:
    workspace = tmp_path / "evidence"

    prepare_workspace(workspace)

    metadata = workspace / "environment-preflight.json"
    inventory = workspace / "SHA256SUMS"

    assert metadata.is_file()
    assert inventory.is_file()

    payload = json.loads(metadata.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "g47-environment-preflight/v1"
    assert payload["certification"]["production_certified"] is False

    inventory_text = inventory.read_text(encoding="utf-8")
    assert "environment-preflight.json" in inventory_text


def test_existing_metadata_is_not_overwritten(tmp_path: Path) -> None:
    workspace = tmp_path / "evidence"
    workspace.mkdir()

    metadata = workspace / "environment-preflight.json"
    metadata.write_text("sentinel\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        prepare_workspace(workspace)

    assert metadata.read_text(encoding="utf-8") == "sentinel\n"


def test_inventory_excludes_itself(tmp_path: Path) -> None:
    workspace = tmp_path / "evidence"
    workspace.mkdir()

    artifact = workspace / "artifact.txt"
    artifact.write_text("test\n", encoding="utf-8")

    inventory = build_inventory(workspace)

    assert [item.relative_path for item in inventory] == ["artifact.txt"]


def test_private_key_names_are_excluded(tmp_path: Path) -> None:
    workspace = tmp_path / "evidence"
    workspace.mkdir()

    private_key = workspace / "id_ed25519"
    private_key.write_text("should-not-be-collected\n", encoding="utf-8")

    inventory = build_inventory(workspace)

    assert all(item.relative_path != "id_ed25519" for item in inventory)


def test_forbidden_private_key_artifact_is_not_in_inventory(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "evidence"
    workspace.mkdir()

    (workspace / "id_ed25519").write_text(
        "PRIVATE-KEY-SENTINEL\n",
        encoding="utf-8",
    )
    (workspace / "safe.txt").write_text(
        "safe\n",
        encoding="utf-8",
    )

    inventory = build_inventory(workspace)
    paths = {item.relative_path for item in inventory}

    assert "safe.txt" in paths
    assert "id_ed25519" not in paths


def test_nested_forbidden_environment_file_is_not_in_inventory(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "evidence"
    nested = workspace / "nested"
    nested.mkdir(parents=True)

    (nested / ".env.production").write_text(
        "SECRET=SENTINEL\n",
        encoding="utf-8",
    )

    inventory = build_inventory(workspace)

    assert all(
        item.relative_path != "nested/.env.production"
        for item in inventory
    )


def test_symlink_artifact_is_not_in_inventory(tmp_path: Path) -> None:
    workspace = tmp_path / "evidence"
    workspace.mkdir()

    target = workspace / "outside.txt"
    target.write_text("outside\n", encoding="utf-8")

    link = workspace / "linked.txt"
    link.symlink_to(target)

    inventory = build_inventory(workspace)

    assert all(item.relative_path != "linked.txt" for item in inventory)


def test_existing_inventory_is_not_overwritten(tmp_path: Path) -> None:
    workspace = tmp_path / "evidence"
    workspace.mkdir()

    sentinel = workspace / "SHA256SUMS"
    sentinel.write_text(
        "DO-NOT-OVERWRITE\n",
        encoding="utf-8",
    )

    from tools.g47.environment_preflight import write_inventory

    with pytest.raises(FileExistsError):
        write_inventory(workspace)

    assert sentinel.read_text(encoding="utf-8") == "DO-NOT-OVERWRITE\n"
