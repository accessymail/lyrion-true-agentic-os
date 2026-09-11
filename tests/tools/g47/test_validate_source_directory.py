from __future__ import annotations

import json
from pathlib import Path

import pytest
from tools.g47.validate_source_directory import (
    SourceDirectoryError,
    build_result,
    inspect_source_directory,
)


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, sort_keys=True),
        encoding="utf-8",
    )


def test_empty_directory_is_not_ready(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()

    assert build_result(source_dir) == 0

    output = capsys.readouterr().out
    assert "RESULT: NOT_READY" in output
    assert "no authoritative JSON sources" in output


def test_absent_directory_is_not_ready(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_dir = tmp_path / "missing"

    assert build_result(source_dir) == 0

    output = capsys.readouterr().out
    assert "RESULT: NOT_READY" in output


def test_valid_complete_source_set_is_ready(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()

    write_json(source_dir / "g46.5-authoritative.json", {"requirements": []})
    write_json(source_dir / "g47-authoritative.json", {"obligations": []})

    assert build_result(source_dir) == 0

    output = capsys.readouterr().out
    assert "G46.5 sources: 1" in output
    assert "G47 sources: 1" in output
    assert "RESULT: READY" in output


def test_invalid_json_is_rejected(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()

    (source_dir / "g46.5-authoritative.json").write_text(
        "{invalid",
        encoding="utf-8",
    )

    with pytest.raises(SourceDirectoryError, match="invalid JSON"):
        inspect_source_directory(source_dir)


def test_duplicate_g46_5_sources_are_rejected(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()

    write_json(source_dir / "g46.5-a.json", {})
    write_json(source_dir / "g46.5-b.json", {})

    with pytest.raises(
        SourceDirectoryError,
        match="duplicate G46.5",
    ):
        build_result(source_dir)


def test_duplicate_g47_sources_are_rejected(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()

    write_json(source_dir / "g46.5-authoritative.json", {})
    write_json(source_dir / "g47-a.json", {})
    write_json(source_dir / "g47-b.json", {})

    with pytest.raises(
        SourceDirectoryError,
        match="duplicate G47",
    ):
        build_result(source_dir)


def test_symlink_source_is_rejected(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()

    target = tmp_path / "target.json"
    write_json(target, {})

    link = source_dir / "g46.5-authoritative.json"
    link.symlink_to(target)

    with pytest.raises(SourceDirectoryError, match="symlink"):
        inspect_source_directory(source_dir)


def test_nested_directory_is_rejected(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    (source_dir / "nested").mkdir()

    with pytest.raises(SourceDirectoryError, match="nested directory"):
        inspect_source_directory(source_dir)


def test_non_json_files_are_ignored_safely(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()

    (source_dir / "README.txt").write_text(
        "not an authoritative source",
        encoding="utf-8",
    )

    assert build_result(source_dir) == 0

    output = capsys.readouterr().out
    assert "ignored non-JSON file: README.txt" in output
    assert "RESULT: NOT_READY" in output


def test_unrecognized_json_is_not_treated_as_authoritative(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()

    write_json(source_dir / "unknown.json", {"data": []})

    assert build_result(source_dir) == 0

    output = capsys.readouterr().out
    assert "no recognized G46.5/G47 filename marker" in output
    assert "RESULT: NOT_READY" in output


def test_ambiguous_filename_is_rejected(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()

    write_json(source_dir / "g46.5-g47-authoritative.json", {})

    with pytest.raises(
        SourceDirectoryError,
        match="ambiguous authoritative-source filename",
    ):
        inspect_source_directory(source_dir)


def test_json_scalar_root_is_rejected(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()

    (source_dir / "g46.5-authoritative.json").write_text(
        '"scalar"',
        encoding="utf-8",
    )

    with pytest.raises(
        SourceDirectoryError,
        match="JSON root must be an object or array",
    ):
        inspect_source_directory(source_dir)
