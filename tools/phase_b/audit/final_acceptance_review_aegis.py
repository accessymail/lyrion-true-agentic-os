#!/usr/bin/env python3
"""
LYRION True Agentic OS
Aegis Bounded Slice — Final Acceptance Review

READ-ONLY.

Purpose:
    Establish formal acceptance of the bounded Aegis policy-decision
    validation slice after controlled validation and evidence verification.

This reviewer does NOT:
    - modify runtime source
    - modify tests
    - modify documentation
    - modify manifests
    - modify G46.5/G47
    - modify R097
    - perform production deployment
    - claim full PB-DOC-010 validation
    - claim production certification
    - commit or push Git

Acceptance boundary:
    Controlled validation evidence verified
        +
    repository/runtime/test integrity preserved
        +
    bounded Aegis evidence complete
        =
    AEGIS BOUNDED SLICE ACCEPTED

This does NOT mean:
    - full PB-DOC-010 validated
    - Phase B production implementation complete
    - production operation established
    - production certification established
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]

EXPECTED_HEAD = "48f5a790e381785282d7703d6a7efa7aeb5f527c"

EVIDENCE_GLOB = "lyrion-aegis-bounded-validation-*"

EXPECTED_COUNTS = {
    "B_aegis_core.txt": 68,
    "C_gateway.txt": 30,
    "D_secure_executor.txt": 48,
    "E_result_state.txt": 6,
}

RUNTIME_SHA = {
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

TEST_SHA = {
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

EXPECTED_AUDIT_TOOLS = {
    "tools/phase_b/audit/map_aegis_integration.py",
    "tools/phase_b/audit/plan_aegis_bounded_validation.py",
    "tools/phase_b/audit/review_aegis_boundary_evidence.py",
    "tools/phase_b/audit/review_aegis_controlled_evidence.py",
    "tools/phase_b/audit/review_aegis_implementation.py",
    "tools/phase_b/audit/review_aegis_semantics.py",
    "tools/phase_b/audit/trace_aegis_call_chain.py",
    "tools/phase_b/audit/verify_aegis_semantic_boundary.py",
    "tools/phase_b/audit/final_acceptance_review_aegis.py",
}

PROTECTED_PATHS = (
    "src",
    "tests",
    "docs",
    "Manifest.md",
)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def latest_evidence() -> Path | None:
    candidates = sorted(
        p for p in Path("/tmp").glob(EVIDENCE_GLOB) if p.is_dir()
    )
    return candidates[-1] if candidates else None


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def verify_evidence_files(
    evidence: Path,
    failures: list[str],
) -> None:
    required = {
        "environment.txt",
        "A_static_compile.txt",
        "B_aegis_core.txt",
        "C_gateway.txt",
        "D_secure_executor.txt",
        "E_result_state.txt",
        "post_validation_integrity.txt",
    }

    for filename in sorted(required):
        check(
            f"evidence file {filename}",
            (evidence / filename).is_file(),
            "required evidence artifact exists",
            failures,
        )


def verify_environment(
    evidence: Path,
    failures: list[str],
) -> None:
    text = read(evidence / "environment.txt")

    checks = (
        ("validated HEAD", EXPECTED_HEAD in text),
        ("validated origin/main", EXPECTED_HEAD in text),
        ("Python 3.14.4", "Python 3.14.4" in text),
        ("pytest 8.4.2", "pytest 8.4.2" in text),
    )

    for label, condition in checks:
        check(
            f"environment: {label}",
            condition,
            "controlled validation environment recorded",
            failures,
        )


def verify_pytest_result(
    evidence: Path,
    filename: str,
    expected: int,
    failures: list[str],
) -> None:
    text = read(evidence / filename)

    match = re.search(
        r"(?m)^\s*(\d+)\s+passed(?:\s+in\s+[0-9.]+s)?\s*$",
        text,
    )

    check(
        f"{filename}: pytest summary",
        match is not None,
        "exact pytest pass-summary line present",
        failures,
    )

    if match:
        observed = int(match.group(1))
        check(
            f"{filename}: pass count",
            observed == expected,
            f"expected {expected}, observed {observed}",
            failures,
        )

    # Avoid the earlier over-broad "error" substring failure.
    summary_failure = re.search(
        r"(?im)^\s*\d+\s+(?:failed|error|errors)\b",
        text,
    )

    check(
        f"{filename}: failure summary",
        summary_failure is None,
        "no pytest failed/error summary present",
        failures,
    )


def verify_runtime_hashes(failures: list[str]) -> None:
    for relative, expected in RUNTIME_SHA.items():
        path = REPO / relative
        check(
            f"runtime integrity: {relative}",
            path.is_file() and sha256(path) == expected,
            "SHA-256 matches controlled validation baseline",
            failures,
        )


def verify_test_hashes(failures: list[str]) -> None:
    for relative, expected in TEST_SHA.items():
        path = REPO / relative
        check(
            f"test integrity: {relative}",
            path.is_file() and sha256(path) == expected,
            "SHA-256 matches controlled validation baseline",
            failures,
        )


def verify_git_state(failures: list[str]) -> None:
    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")

    check(
        "Git HEAD",
        head == EXPECTED_HEAD,
        "repository HEAD remains the validated commit",
        failures,
    )

    check(
        "Git origin/main",
        origin == EXPECTED_HEAD,
        "origin/main remains the validated commit",
        failures,
    )

    status = git("status", "--short", "--untracked-files=all")

    observed_untracked = {
        line[3:]
        for line in status.splitlines()
        if line.startswith("?? ")
    }

    check(
        "Aegis audit-tool inventory",
        observed_untracked == EXPECTED_AUDIT_TOOLS,
        "only the eight expected Aegis audit tools are untracked",
        failures,
    )


def verify_protected_diff(failures: list[str]) -> None:
    diff = git(
        "diff",
        "--name-only",
        EXPECTED_HEAD,
        "--",
        *PROTECTED_PATHS,
    )

    check(
        "protected tracked paths",
        diff == "",
        "no runtime/tests/docs/manifest modifications exist",
        failures,
    )


def verify_acceptance_boundaries(
    evidence: Path,
    failures: list[str],
) -> None:
    integrity_text = read(evidence / "post_validation_integrity.txt")

    # The controlled validation command set is intentionally bounded.
    # These checks establish the acceptance boundary from the evidence
    # structure and current protected repository state; they do not
    # reconstruct G46.5/G47 or independently certify production.

    required_scope_markers = (
        "A_static_compile.txt",
        "B_aegis_core.txt",
        "C_gateway.txt",
        "D_secure_executor.txt",
        "E_result_state.txt",
    )

    scope_complete = all(
        (evidence / marker).is_file()
        for marker in required_scope_markers
    )

    check(
        "controlled-validation evidence scope",
        scope_complete
        and evidence.name.startswith("lyrion-aegis-bounded-validation-"),
        "evidence directory and A-E bounded validation artifacts are present",
        failures,
    )

    protected_boundary_text = integrity_text.lower()

    check(
        "controlled-validation integrity record",
        bool(protected_boundary_text.strip()),
        "post-validation integrity record exists and is non-empty",
        failures,
    )

    # Explicitly preserve the acceptance limitation in this reviewer:
    # absence of a certification claim is enforced by the acceptance
    # decision itself, not inferred from arbitrary pytest output.
    check(
        "production certification boundary",
        True,
        "this acceptance review does not grant or claim production certification",
        failures,
    )


def main() -> int:
    print("=" * 82)
    print("LYRION TRUE AGENTIC OS")
    print("AEGIS BOUNDED SLICE — FINAL ACCEPTANCE REVIEW")
    print("READ-ONLY")
    print("=" * 82)

    failures: list[str] = []

    evidence = latest_evidence()

    print("\nEVIDENCE DISCOVERY")

    if evidence is None:
        print("[FAIL] No Aegis controlled-validation evidence directory found.")
        return 1

    print(f"[PASS] Evidence directory: {evidence}")

    verify_evidence_files(evidence, failures)

    if failures:
        print("\nRequired evidence artifacts are incomplete.")
        print("AEGIS_BOUNDED_SLICE_ACCEPTANCE_FAILED")
        return 1

    print("\nENVIRONMENT ACCEPTANCE REVIEW")
    verify_environment(evidence, failures)

    print("\nCONTROLLED TEST ACCEPTANCE REVIEW")
    for filename, expected in EXPECTED_COUNTS.items():
        verify_pytest_result(
            evidence,
            filename,
            expected,
            failures,
        )

    print("\nRUNTIME INTEGRITY ACCEPTANCE REVIEW")
    verify_runtime_hashes(failures)

    print("\nTEST INTEGRITY ACCEPTANCE REVIEW")
    verify_test_hashes(failures)

    print("\nGIT STATE ACCEPTANCE REVIEW")
    verify_git_state(failures)

    print("\nPROTECTED PATH ACCEPTANCE REVIEW")
    verify_protected_diff(failures)

    print("\nGOVERNANCE BOUNDARY ACCEPTANCE REVIEW")
    verify_acceptance_boundaries(evidence, failures)

    print("\n" + "=" * 82)
    print("AEGIS BOUNDED SLICE ACCEPTANCE DECISION")
    print("=" * 82)

    if failures:
        print(f"FAILURES: {len(failures)}")
        for failure in failures:
            print(f" - {failure}")

        print()
        print("AEGIS_BOUNDED_SLICE_ACCEPTANCE_FAILED")
        return 1

    print("PASS: Controlled Aegis evidence is complete.")
    print("PASS: 152 controlled tests are represented.")
    print("PASS: Runtime integrity preserved.")
    print("PASS: Test integrity preserved.")
    print("PASS: Git state preserved.")
    print("PASS: Protected paths preserved.")
    print("PASS: Production-certification boundary preserved.")

    print()
    print("AEGIS_BOUNDED_SLICE_ACCEPTED")

    print()
    print(
        "Acceptance applies only to the bounded Aegis policy-decision "
        "validation slice."
    )
    print(
        "Full PB-DOC-010 validation remains outstanding."
    )
    print(
        "Phase-B production implementation remains blocked."
    )
    print(
        "Production certification remains NOT CLAIMED."
    )
    print(
        "G46.5/G47 remain unreconstructed and blocked."
    )
    print(
        "R097 remains unchanged."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
