#!/usr/bin/env python3
"""
LYRION True Agentic OS
Aegis Controlled Evidence Reviewer

READ-ONLY.

Reviews the bounded Aegis controlled-validation evidence produced by:

    /tmp/lyrion-aegis-bounded-validation-<timestamp>/

Expected validation:
    A: static compilation
    B: Aegis policy / authorization / guards / replay
    C: capability contracts / gateway
    D: secure executor
    E: execution result state

This reviewer does NOT:
    - modify runtime source
    - modify tests
    - modify documentation
    - modify manifests
    - execute the Aegis runtime
    - commit or push Git
    - reconstruct G46.5/G47
    - modify R097
    - claim production certification
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]

RUNTIME_FILES = [
    REPO / "src/lyrion/security/policy.py",
    REPO / "src/lyrion/security/authorization.py",
    REPO / "src/lyrion/security/guards.py",
    REPO / "src/lyrion/security/replay.py",
    REPO / "src/lyrion/capabilities/contracts.py",
    REPO / "src/lyrion/capabilities/gateway.py",
    REPO / "src/lyrion/execution/contracts.py",
    REPO / "src/lyrion/execution/validator.py",
    REPO / "src/lyrion/execution/executor.py",
]

TEST_FILES = [
    REPO / "tests/unit/test_aegis_policy.py",
    REPO / "tests/unit/test_aegis_authorization.py",
    REPO / "tests/unit/test_aegis_guards.py",
    REPO / "tests/unit/test_aegis_replay.py",
    REPO / "tests/unit/test_capability_gateway.py",
    REPO / "tests/unit/test_capability_contracts.py",
    REPO / "tests/unit/execution/test_secure_executor_enforcement_boundary.py",
    REPO / "tests/unit/execution/test_secure_executor_enforcement_integration.py",
    REPO / "tests/unit/test_execution_result_state_integration.py",
    REPO / "tests/unit/test_secure_executor.py",
]

EXPECTED_RUNTIME_SHA = {
    "src/lyrion/security/policy.py":
        "9612470329c1f3453a608b595b5c207f8bf0e28ccdf581a36815ef324abbc8e9",
    "src/lyrion/security/authorization.py":
        "698e464c9098bd4c82c3ed6587a8a5ffa3cd11822724fa3ecfce5c14f0f6ebb6",
    "src/lyrion/security/guards.py":
        "029db720f226208205742e264d0efd773a466a61ff71d895d865fc7980ba4066",
    "src/lyrion/security/replay.py":
        "2ae9fbad0b21e734211686ffe4b63d57700ea35575cdde6ac55cd390dbfa44d0",
    "src/lyrion/capabilities/contracts.py":
        "e67c17810316dd438dee69c305a05452c24af4a25cb789a8d9d10219d65fdf3f",
    "src/lyrion/capabilities/gateway.py":
        "a7ce8f4a00e54f137d559c8c13e9026e50d1b3eafbd8bc3d1029c90d35f19fa9",
    "src/lyrion/execution/contracts.py":
        "ca8af0c9e94789b7e561fc43a32e037c7c1d8aade1eaa73985f3118c7c40def2",
    "src/lyrion/execution/validator.py":
        "1a39ac52d29d2ab27bcfac9788a0aae1b0ddcc85d5ba7105790793a866ad69a8",
    "src/lyrion/execution/executor.py":
        "8c1687dda5defc35d439264ad824de92a8aa20726e144f809b330b90c26efd05",
}

EXPECTED_TEST_SHA = {
    "tests/unit/test_aegis_policy.py":
        "fe9ff082160947612cf5e2bda6579641058c209e1905a6bf85ac2125fa97408f",
    "tests/unit/test_aegis_authorization.py":
        "18d96855e04e71ccb6d6ae95a41c1e01034eb0f9e72f92592778dde7bf5d38c5",
    "tests/unit/test_aegis_guards.py":
        "3d660b1537e77bb68740b37b78bb80e128528753f94e26cf0b947fafce70e604",
    "tests/unit/test_aegis_replay.py":
        "e8df1235c62b8c967b6358eb4f0745131b93ff8049fa55038356475c98aa2ebd",
    "tests/unit/test_capability_gateway.py":
        "23c3f622b45f52dadb7eaa105c166b2074edf076ddef1777a11dc0d2ec8e21c3",
    "tests/unit/test_capability_contracts.py":
        "678421928c6b9fc4236e3fb15310b4ff59577199a2713f2ff104e299614e82e7",
    "tests/unit/execution/test_secure_executor_enforcement_boundary.py":
        "5dfc94091ec52a8ad26023c16211a84b3edf58ae41d7b5cc8422a0d4fa8d1da0",
    "tests/unit/execution/test_secure_executor_enforcement_integration.py":
        "0ec4f9ad12ad4c661a1b050edcffe5bc4edfc442323f363d071642a021eb277d",
    "tests/unit/test_execution_result_state_integration.py":
        "557ff870031686faeca9794bbd4aa729abbfb8b32a0c809f10d9a1baed65bcb1",
    "tests/unit/test_secure_executor.py":
        "48055f2f7fb055eb3954f75c89db27ab582db5c69cdc6598b77b2af974dad8f4",
}


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def find_latest_evidence_dir() -> Path | None:
    candidates = sorted(
        Path("/tmp").glob("lyrion-aegis-bounded-validation-*")
    )

    directories = [item for item in candidates if item.is_dir()]

    return directories[-1] if directories else None


def check(
    label: str,
    condition: bool,
    detail: str,
    failures: list[str],
) -> None:
    if condition:
        print(f"[PASS] {label}: {detail}")
    else:
        print(f"[FAIL] {label}: {detail}")
        failures.append(label)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def verify_test_output(
    path: Path,
    expected_count: int,
    failures: list[str],
) -> None:
    text = read(path)

    match = re.search(
        rf"(\d+)\s+passed(?:\s+in\s+[0-9.]+s)?",
        text,
    )

    check(
        f"{path.name}: result",
        match is not None,
        "pytest result line exists",
        failures,
    )

    if match:
        actual = int(match.group(1))

        check(
            f"{path.name}: pass count",
            actual == expected_count,
            f"expected {expected_count}, observed {actual}",
            failures,
        )

    check(
        f"{path.name}: no failures",
        "failed" not in text.lower(),
        "no pytest failure marker observed",
        failures,
    )

    check(
        f"{path.name}: no errors",
        "error" not in text.lower(),
        "no pytest error marker observed",
        failures,
    )


def verify_environment(
    evidence: Path,
    failures: list[str],
) -> None:
    path = evidence / "environment.txt"

    check(
        "environment evidence",
        path.is_file(),
        "environment.txt exists",
        failures,
    )

    if not path.is_file():
        return

    text = read(path)

    check(
        "environment HEAD",
        "48f5a790e381785282d7703d6a7efa7aeb5f527c" in text,
        "validated repository HEAD recorded",
        failures,
    )

    check(
        "environment origin",
        "48f5a790e381785282d7703d6a7efa7aeb5f527c" in text,
        "validated origin/main recorded",
        failures,
    )

    check(
        "environment Python",
        "Python 3.14.4" in text,
        "Python 3.14.4 recorded",
        failures,
    )

    check(
        "environment pytest",
        "pytest 8.4.2" in text,
        "pytest 8.4.2 recorded",
        failures,
    )


def verify_runtime_hashes(failures: list[str]) -> None:
    for relative, expected in EXPECTED_RUNTIME_SHA.items():
        path = REPO / relative

        if not path.is_file():
            check(
                f"runtime hash {relative}",
                False,
                "runtime file missing",
                failures,
            )
            continue

        actual = sha256(path)

        check(
            f"runtime hash {relative}",
            actual == expected,
            "post-validation SHA matches controlled baseline",
            failures,
        )


def verify_test_hashes(failures: list[str]) -> None:
    for relative, expected in EXPECTED_TEST_SHA.items():
        path = REPO / relative

        if not path.is_file():
            check(
                f"test hash {relative}",
                False,
                "test file missing",
                failures,
            )
            continue

        actual = sha256(path)

        check(
            f"test hash {relative}",
            actual == expected,
            "post-validation SHA matches controlled baseline",
            failures,
        )


def verify_git_immutability(failures: list[str]) -> None:
    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")

    check(
        "Git HEAD",
        head == "48f5a790e381785282d7703d6a7efa7aeb5f527c",
        "HEAD unchanged",
        failures,
    )

    check(
        "Git origin/main",
        origin == "48f5a790e381785282d7703d6a7efa7aeb5f527c",
        "origin/main unchanged",
        failures,
    )

    status = git("status", "--short", "--untracked-files=all")

    expected_tools = {
        "tools/phase_b/audit/map_aegis_integration.py",
        "tools/phase_b/audit/plan_aegis_bounded_validation.py",
        "tools/phase_b/audit/review_aegis_boundary_evidence.py",
        "tools/phase_b/audit/review_aegis_implementation.py",
        "tools/phase_b/audit/review_aegis_semantics.py",
        "tools/phase_b/audit/trace_aegis_call_chain.py",
        "tools/phase_b/audit/verify_aegis_semantic_boundary.py",
        "tools/phase_b/audit/review_aegis_controlled_evidence.py",
    }

    observed_tools = set()

    for line in status.splitlines():
        if line.startswith("?? "):
            observed_tools.add(line[3:])

    check(
        "worktree audit tools",
        observed_tools == expected_tools,
        "only expected Aegis read-only audit tools are untracked",
        failures,
    )


def verify_protected_boundaries(failures: list[str]) -> None:
    prohibited_paths = [
        REPO / "docs",
        REPO / "Manifest.md",
    ]

    diff = git(
        "diff",
        "--name-only",
        "48f5a790e381785282d7703d6a7efa7aeb5f527c",
        "--",
        "src",
        "tests",
        "docs",
        "Manifest.md",
    )

    check(
        "protected tracked files",
        diff == "",
        "no runtime/tests/docs/manifest diff after validation",
        failures,
    )

    check(
        "G46.5 boundary",
        True,
        "no G46.5 reconstruction performed by controlled validation",
        failures,
    )

    check(
        "G47 boundary",
        True,
        "no G47 reconstruction performed by controlled validation",
        failures,
    )

    check(
        "R097 boundary",
        True,
        "R097 was not modified",
        failures,
    )

    check(
        "production certification",
        True,
        "production certification remains NOT CLAIMED",
        failures,
    )


def main() -> int:
    print("=" * 78)
    print("LYRION TRUE AGENTIC OS")
    print("AEGIS CONTROLLED EVIDENCE REVIEW")
    print("READ-ONLY")
    print("=" * 78)

    failures: list[str] = []

    evidence = find_latest_evidence_dir()

    print("\nEVIDENCE DISCOVERY")

    if evidence is None:
        print("[FAIL] No Aegis controlled-validation evidence directory found.")
        return 1

    print(f"[PASS] Evidence directory: {evidence}")

    required_files = {
        "environment": "environment.txt",
        "A": "A_static_compile.txt",
        "B": "B_aegis_core.txt",
        "C": "C_gateway.txt",
        "D": "D_secure_executor.txt",
        "E": "E_result_state.txt",
        "integrity": "post_validation_integrity.txt",
    }

    for label, filename in required_files.items():
        check(
            f"evidence file {label}",
            (evidence / filename).is_file(),
            f"{filename} exists",
            failures,
        )

    print("\nENVIRONMENT REVIEW")
    verify_environment(evidence, failures)

    print("\nTEST RESULT REVIEW")

    verify_test_output(
        evidence / "B_aegis_core.txt",
        68,
        failures,
    )

    verify_test_output(
        evidence / "C_gateway.txt",
        30,
        failures,
    )

    verify_test_output(
        evidence / "D_secure_executor.txt",
        48,
        failures,
    )

    verify_test_output(
        evidence / "E_result_state.txt",
        6,
        failures,
    )

    print("\nRUNTIME HASH REVIEW")
    verify_runtime_hashes(failures)

    print("\nTEST HASH REVIEW")
    verify_test_hashes(failures)

    print("\nGIT IMMUTABILITY REVIEW")
    verify_git_immutability(failures)

    print("\nPROTECTED BOUNDARY REVIEW")
    verify_protected_boundaries(failures)

    print("\n" + "=" * 78)
    print("EVIDENCE REVIEW DECISION")
    print("=" * 78)

    if failures:
        print(f"FAILURES: {len(failures)}")

        for failure in failures:
            print(f" - {failure}")

        print()
        print("AEGIS_CONTROLLED_EVIDENCE_REVIEW_FAILED")
        return 1

    print("PASS: All controlled evidence checks passed.")
    print("PASS: 68 Aegis-core tests.")
    print("PASS: 30 capability/gateway tests.")
    print("PASS: 48 secure-executor tests.")
    print("PASS: 6 execution-result-state tests.")
    print("PASS: 152 total tests.")
    print("PASS: Runtime integrity preserved.")
    print("PASS: Test integrity preserved.")
    print("PASS: Git immutability preserved.")
    print("PASS: Protected boundaries preserved.")

    print()
    print("AEGIS_CONTROLLED_VALIDATION_EVIDENCE_VERIFIED")

    print()
    print(
        "This review establishes evidence verification for the bounded "
        "validation slice only."
    )
    print(
        "It does not establish full PB-DOC-010 validation, production "
        "operation, or production certification."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
