from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DISCOVER = PROJECT_ROOT / "tools/g47/discover_authoritative_sources.py"
INGEST = PROJECT_ROOT / "tools/g47/ingest_authoritative_sources.py"
VERIFY = PROJECT_ROOT / "tools/g47/verify_authoritative_sources.py"
MANIFEST = PROJECT_ROOT / "tools/g47/create_source_manifest.py"
VALIDATE = PROJECT_ROOT / "tools/g47/validate_source_directory.py"


def run_tool(
    script: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def synthetic_sources(tmp_path: Path) -> tuple[Path, Path]:
    source_dir = tmp_path / "authoritative-input"
    source_dir.mkdir()

    g46_5 = source_dir / "g46.5-authoritative.json"
    g47 = source_dir / "g47-authoritative.json"

    write_json(
        g46_5,
        {
            "requirements": [
                {
                    "id": "G46.5-SYNTH-001",
                    "category": "SYNTHETIC_TEST",
                    "status": "implemented",
                }
            ]
        },
    )

    write_json(
        g47,
        {
            "obligations": [
                {
                    "id": "G47-SYNTH-001",
                    "requirement_id": "G46.5-SYNTH-001",
                    "status": "pending",
                }
            ]
        },
    )

    return g46_5, g47


def test_discovery_finds_synthetic_authoritative_sources(
    synthetic_sources: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    g46_5, g47 = synthetic_sources

    result = run_tool(
        DISCOVER,
        str(g46_5.parent),
    )

    assert result.returncode == 0, result.stderr
    assert g46_5.name in result.stdout
    assert g47.name in result.stdout


def test_ingestion_copies_without_overwriting(
    synthetic_sources: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    g46_5, g47 = synthetic_sources
    destination = tmp_path / "sources"
    destination.mkdir()

    result = run_tool(
        INGEST,
        "--g46-5",
        str(g46_5),
        "--g47",
        str(g47),
        "--destination",
        str(destination),
    )
    assert result.returncode == 0, result.stderr

    assert (destination / g46_5.name).read_bytes() == g46_5.read_bytes()
    assert (destination / g47.name).read_bytes() == g47.read_bytes()

    before = (destination / g46_5.name).read_bytes()

    second = run_tool(
        INGEST,
        "--g46-5",
        str(g46_5),
        "--g47",
        str(g47),
        "--destination",
        str(destination),
    )

    assert second.returncode != 0
    assert (destination / g46_5.name).read_bytes() == before


def test_ingestion_rejects_symlink_source(
    synthetic_sources: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    g46_5, _ = synthetic_sources
    symlink = tmp_path / "g46.5-authoritative.json"
    symlink.symlink_to(g46_5)

    destination = tmp_path / "sources"
    destination.mkdir()

    result = run_tool(
        INGEST,
        "--source",
        str(symlink),
        "--destination",
        str(destination),
    )

    assert result.returncode != 0


def test_validation_accepts_synthetic_complete_set(
    synthetic_sources: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    g46_5, g47 = synthetic_sources
    destination = tmp_path / "sources"
    destination.mkdir()

    result = run_tool(
        INGEST,
        "--g46-5",
        str(g46_5),
        "--g47",
        str(g47),
        "--destination",
        str(destination),
    )
    assert result.returncode == 0, result.stderr

    result = run_tool(
        VALIDATE,
        "--source-directory",
        str(destination),
    )

    assert result.returncode == 0, result.stderr
    assert "G46.5 sources: 1" in result.stdout
    assert "G47 sources: 1" in result.stdout
    assert "RESULT: READY" in result.stdout


def test_manifest_contains_expected_hashes(
    synthetic_sources: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    g46_5, g47 = synthetic_sources
    destination = tmp_path / "sources"
    destination.mkdir()

    result = run_tool(
        INGEST,
        "--g46-5",
        str(g46_5),
        "--g47",
        str(g47),
        "--destination",
        str(destination),
    )
    assert result.returncode == 0, result.stderr

    manifest = tmp_path / "source-manifest.txt"

    result = run_tool(
        MANIFEST,
        "--g46-5",
        str(destination / g46_5.name),
        "--g47",
        str(destination / g47.name),
        "--output",
        str(manifest),
    )

    assert result.returncode == 0, result.stderr
    assert manifest.is_file()

    contents = manifest.read_text(encoding="utf-8")

    assert sha256(g46_5) in contents
    assert sha256(g47) in contents


def test_verify_rejects_modified_ingested_source(
    synthetic_sources: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    g46_5, g47 = synthetic_sources
    destination = tmp_path / "sources"
    destination.mkdir()

    result = run_tool(
        INGEST,
        "--g46-5",
        str(g46_5),
        "--g47",
        str(g47),
        "--destination",
        str(destination),
    )
    assert result.returncode == 0, result.stderr

    target = destination / g46_5.name
    original = target.read_bytes()

    target.write_bytes(original + b"\n")

    result = run_tool(
        VERIFY,
        "--source-directory",
        str(destination),
    )

    assert result.returncode != 0


def test_real_source_directory_is_never_modified(
    synthetic_sources: tuple[Path, Path],
) -> None:
    del synthetic_sources

    real_directory = PROJECT_ROOT / "docs/g47/sources"
    before = sorted(
        path.relative_to(real_directory).as_posix()
        for path in real_directory.iterdir()
    )

    assert not any(real_directory.iterdir())

    after = sorted(
        path.relative_to(real_directory).as_posix()
        for path in real_directory.iterdir()
    )

    assert before == after == []


def test_pipeline_does_not_promote_synthetic_data_to_real_sources(
    synthetic_sources: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    g46_5, g47 = synthetic_sources
    synthetic_destination = tmp_path / "synthetic-sources"
    synthetic_destination.mkdir()

    result = run_tool(
        INGEST,
        "--g46-5",
        str(g46_5),
        "--g47",
        str(g47),
        "--destination",
        str(synthetic_destination),
    )
    assert result.returncode == 0, result.stderr

    real_directory = PROJECT_ROOT / "docs/g47/sources"

    assert not any(real_directory.iterdir())


def test_ingestion_rolls_back_first_artifact_when_second_fails(
    synthetic_sources: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    g46_5, g47 = synthetic_sources
    destination = tmp_path / "sources"
    destination.mkdir()

    invalid_g47 = tmp_path / "g47-invalid.txt"
    invalid_g47.write_text("not a JSON source", encoding="utf-8")

    result = run_tool(
        INGEST,
        "--g46-5",
        str(g46_5),
        "--g47",
        str(invalid_g47),
        "--destination",
        str(destination),
    )

    assert result.returncode != 0
    assert not (destination / g46_5.name).exists()
    assert not (destination / invalid_g47.name).exists()


def test_manifest_refuses_existing_output(
    synthetic_sources: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    g46_5, g47 = synthetic_sources
    manifest = tmp_path / "source-manifest.json"
    original = '{"sentinel": true}\n'
    manifest.write_text(original, encoding="utf-8")

    result = run_tool(
        MANIFEST,
        "--g46-5",
        str(g46_5),
        "--g47",
        str(g47),
        "--output",
        str(manifest),
    )

    assert result.returncode != 0
    assert manifest.read_text(encoding="utf-8") == original
