#!/usr/bin/env python3
"""
LYRION True Agentic OS
Phase-B Repository Evidence Classification & Traceability Audit v4

READ-ONLY / FAIL-CLOSED / NO IMPLEMENTATION

Evidence classes:

    DOCUMENTED
        ↓
    DESIGNED
        ↓
    RUNTIME_IMPLEMENTATION_PRESENT
        ↓
    PROJECT_TESTS_PRESENT
        ↓
    VALIDATION_TOOLING_PRESENT
        ↓
    EXECUTED_VALIDATION_EVIDENCE_PRESENT
        ↓
    ACCEPTANCE_EVIDENCE_PRESENT

Important:
    Presence of a file is NOT proof that the implementation works.
    Presence of a test is NOT proof that the test passed.
    Presence of validation tooling is NOT proof that validation passed.
    Production certification is governed separately.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[3]

SRC_ROOT = REPO_ROOT / "src"
TEST_ROOTS = (
    REPO_ROOT / "tests",
)

DOCS_ROOT = REPO_ROOT / "docs" / "phase-b"
TOOLS_ROOT = REPO_ROOT / "tools" / "phase_b"

MASTER_MANIFEST = (
    DOCS_ROOT
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

PB_DOC_021 = (
    DOCS_ROOT
    / "governance"
    / "LYRION_PHASE_B_IMPLEMENTATION_AUTHORIZATION_GATE_SPECIFICATION_v1.md"
)

# ---------------------------------------------------------------------------
# Repository exclusion boundary
# ---------------------------------------------------------------------------

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
    ".tox",
}

EXCLUDED_ROOTS = (
    REPO_ROOT / "NOT_USABLE_DOCUMENTS",
)


SOURCE_SUFFIXES = {
    ".py",
    ".rs",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
}


@dataclass(frozen=True)
class Finding:
    category: str
    status: str
    subject: str
    detail: str


@dataclass(frozen=True)
class EvidenceProfile:
    name: str
    source_paths: tuple[str, ...]
    source_terms: tuple[str, ...]
    test_terms: tuple[str, ...]
    validation_terms: tuple[str, ...]


PROFILES: tuple[EvidenceProfile, ...] = (
    EvidenceProfile(
        name="Governed task / agent identity boundary",
        source_paths=(
            "src/lyrion/tasks/",
            "src/lyrion/application/",
            "src/lyrion/cognition/",
        ),
        source_terms=(
            "principal",
            "agent_identity",
            "agent identity",
            "task_identity",
            "task identity",
            "authority",
        ),
        test_terms=(
            "identity",
            "principal",
            "agent",
            "authority",
            "task",
        ),
        validation_terms=(
            "identity",
            "principal",
            "agent",
            "authority",
        ),
    ),
    EvidenceProfile(
        name="Execution admission boundary",
        source_paths=(
            "src/lyrion/execution/",
            "src/lyrion/capabilities/",
        ),
        source_terms=(
            "execution_admission",
            "execution admission",
            "admission",
        ),
        test_terms=(
            "execution_admission",
            "execution admission",
            "admission",
        ),
        validation_terms=(
            "execution_admission",
            "execution admission",
            "admission",
        ),
    ),
    EvidenceProfile(
        name="Aegis policy decision boundary",
        source_paths=(
            "src/lyrion/security/",
            "src/lyrion/capabilities/",
        ),
        source_terms=(
            "aegis",
            "policy_decision",
            "policy decision",
            "authorization",
            "policy",
        ),
        test_terms=(
            "aegis",
            "policy",
            "authorization",
        ),
        validation_terms=(
            "aegis",
            "policy",
            "authorization",
        ),
    ),
    EvidenceProfile(
        name="Secure executor boundary",
        source_paths=(
            "src/lyrion/execution/",
        ),
        source_terms=(
            "secure_executor",
            "secure executor",
            "executor",
        ),
        test_terms=(
            "secure_executor",
            "secure executor",
            "executor",
        ),
        validation_terms=(
            "secure_executor",
            "secure executor",
            "executor",
        ),
    ),
    EvidenceProfile(
        name="Agent sandbox boundary",
        source_paths=(
            "src/lyrion/execution/",
        ),
        source_terms=(
            "sandbox",
            "isolation",
            "namespace",
            "seccomp",
            "landlock",
        ),
        test_terms=(
            "sandbox",
            "isolation",
            "namespace",
            "seccomp",
            "landlock",
        ),
        validation_terms=(
            "sandbox",
            "isolation",
            "namespace",
            "seccomp",
            "landlock",
        ),
    ),
    EvidenceProfile(
        name="LHICF host integration boundary",
        source_paths=(
            "src/lyrion/execution/backends/linux/host/",
        ),
        source_terms=(
            "lhicf",
            "host integration",
            "host_integration",
            "host",
        ),
        test_terms=(
            "lhicf",
            "host integration",
            "host_integration",
            "host",
        ),
        validation_terms=(
            "lhicf",
            "host integration",
            "host_integration",
            "host",
        ),
    ),
    EvidenceProfile(
        name="Verification / provenance boundary",
        source_paths=(
            "src/lyrion/execution/",
            "src/lyrion/observability/",
            "src/lyrion/state/",
            "src/lyrion/events/",
        ),
        source_terms=(
            "verification",
            "provenance",
            "integrity",
            "audit",
        ),
        test_terms=(
            "verification",
            "provenance",
            "integrity",
            "audit",
        ),
        validation_terms=(
            "verification",
            "provenance",
            "integrity",
            "audit",
        ),
    ),
)


TEST_FILE_PATTERNS = (
    re.compile(r"^test_.*\.py$", re.I),
    re.compile(r".*_test\.py$", re.I),
    re.compile(r"^test_.*\.rs$", re.I),
    re.compile(r".*_test\.rs$", re.I),
    re.compile(r"^test_.*\.(ts|tsx|js|jsx)$", re.I),
    re.compile(r".*\.(test|spec)\.(ts|tsx|js|jsx)$", re.I),
    re.compile(r".*_test\.go$", re.I),
)


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def read_text(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return ""


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def contains_any(
    text: str,
    terms: Iterable[str],
) -> bool:
    value = normalize(text)

    return any(
        normalize(term) in value
        for term in terms
    )


def relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def is_excluded(path: Path) -> bool:
    parts = set(path.parts)

    if parts & EXCLUDED_PARTS:
        return True

    for root in EXCLUDED_ROOTS:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            pass

    return False


def inventory_files(root: Path) -> list[Path]:
    if not root.exists():
        return []

    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and not is_excluded(path)
    )


def is_test_filename(path: Path) -> bool:
    return any(
        pattern.match(path.name)
        for pattern in TEST_FILE_PATTERNS
    )


def source_files() -> list[Path]:
    """
    Runtime implementation candidates.

    Only repository-owned src/** is inspected.
    """

    return sorted(
        path
        for path in inventory_files(SRC_ROOT)
        if path.suffix.lower() in SOURCE_SUFFIXES
        and not is_test_filename(path)
    )


def project_test_files() -> list[Path]:
    """
    Project-owned tests ONLY.

    Deliberately excludes:
        .venv
        dependencies
        NOT_USABLE_DOCUMENTS
        build/dist/generated trees
    """

    result: list[Path] = []

    for root in TEST_ROOTS:
        for path in inventory_files(root):
            if path.suffix.lower() in SOURCE_SUFFIXES:
                result.append(path)

    return sorted(set(result))


def validation_files() -> list[Path]:
    """
    Phase-B validation tooling.

    These files are NEVER runtime implementation evidence.
    """

    return sorted(
        path
        for path in inventory_files(TOOLS_ROOT)
        if any(
            token in path.name.lower()
            for token in (
                "audit",
                "validate",
                "validation",
                "verify",
                "qualif",
                "review",
                "gate",
                "check",
                "acceptance",
                "negative",
            )
        )
    )


def documentation_files() -> list[Path]:
    return inventory_files(DOCS_ROOT)


def path_matches_prefix(
    path: Path,
    prefixes: Iterable[str],
) -> bool:
    rel = relative(path)

    for prefix in prefixes:
        clean = prefix.rstrip("/")

        if rel == clean:
            return True

        if rel.startswith(clean + "/"):
            return True

    return False


def matching_source_files(
    profile: EvidenceProfile,
    files: Iterable[Path],
) -> list[Path]:
    result: list[Path] = []

    for path in files:
        if not path_matches_prefix(
            path,
            profile.source_paths,
        ):
            continue

        if contains_any(
            read_text(path),
            profile.source_terms,
        ):
            result.append(path)

    return sorted(set(result))


def matching_test_files(
    profile: EvidenceProfile,
    files: Iterable[Path],
) -> list[Path]:
    result: list[Path] = []

    for path in files:
        if contains_any(
            read_text(path),
            profile.test_terms,
        ):
            result.append(path)

    return sorted(set(result))


def matching_validation_files(
    profile: EvidenceProfile,
    files: Iterable[Path],
) -> list[Path]:
    result: list[Path] = []

    for path in files:
        if contains_any(
            read_text(path),
            profile.validation_terms,
        ):
            result.append(path)

    return sorted(set(result))


def matching_documentation_files(
    profile: EvidenceProfile,
    files: Iterable[Path],
) -> list[Path]:
    return sorted(
        path
        for path in files
        if contains_any(
            read_text(path),
            profile.source_terms,
        )
    )


def extract_governance_state(
    text: str,
) -> dict[str, str]:
    """
    Supports Markdown table and key/value forms.
    """

    state: dict[str, str] = {}

    patterns = {
        "Architecture Approval": (
            r"architecture\s+approval"
            r"\s*(?:\*\*)?\s*(?:\||:)\s*"
            r"(approved|pending|blocked|denied|not\s+authorized)"
        ),
        "Implementation Authorization": (
            r"implementation\s+authorization"
            r"\s*(?:\*\*)?\s*(?:\||:)\s*"
            r"(authorized|not\s+authorized|pending|denied|blocked)"
        ),
        "Production Implementation": (
            r"production\s+implementation"
            r"\s*(?:\*\*)?\s*(?:\||:)\s*"
            r"(blocked|authorized|not\s+authorized|pending|active)"
        ),
        "Production Certification": (
            r"production\s+certification"
            r"\s*(?:\*\*)?\s*(?:\||:)\s*"
            r"(not\s+claimed|certified|pending|blocked)"
        ),
    }

    for key, pattern in patterns.items():
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            state[key] = re.sub(
                r"\s+",
                " ",
                match.group(1).upper(),
            )

    return state


def print_section(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def main() -> int:
    findings: list[Finding] = []

    print("LYRION TRUE AGENTIC OS")
    print("PHASE-B REPOSITORY EVIDENCE CLASSIFICATION & TRACEABILITY AUDIT v4")
    print("READ-ONLY / PROJECT-OWNED EVIDENCE / FAIL-CLOSED")
    print()

    # =====================================================================
    # 1. Repository safety
    # =====================================================================

    print_section("1. REPOSITORY SAFETY")

    root = run_git("rev-parse", "--show-toplevel")
    head = run_git("rev-parse", "HEAD")
    branch = run_git("branch", "--show-current")
    status = run_git("status", "--short")

    print(f"Repository : {root}")
    print(f"Branch     : {branch}")
    print(f"HEAD       : {head}")
    print(f"Clean      : {'YES' if not status else 'NO'}")

    findings.append(
        Finding(
            "REPOSITORY",
            "PASS" if branch == "main" else "WARN",
            "branch",
            branch,
        )
    )

    findings.append(
        Finding(
            "REPOSITORY",
            "PASS" if not status else "WARN",
            "working_tree",
            "clean" if not status else "audit changes present",
        )
    )

    # =====================================================================
    # 2. Governance
    # =====================================================================

    print_section("2. GOVERNANCE BASELINE")

    for path in (
        MASTER_MANIFEST,
        PB_DOC_021,
    ):
        if not path.is_file():
            print(f"[FAIL] Missing: {relative(path)}")

            findings.append(
                Finding(
                    "GOVERNANCE",
                    "FAIL",
                    path.name,
                    "missing",
                )
            )
        else:
            print(f"[PRESENT] {relative(path)}")
            print(f"          SHA256 {sha256_file(path)}")

            findings.append(
                Finding(
                    "GOVERNANCE",
                    "PASS",
                    path.name,
                    "present",
                )
            )

    governance_state = extract_governance_state(
        read_text(MASTER_MANIFEST)
    )

    expected_state = {
        "Architecture Approval": "APPROVED",
        "Implementation Authorization": "AUTHORIZED",
        "Production Implementation": "BLOCKED",
        "Production Certification": "NOT CLAIMED",
    }

    print()
    print("Parsed Master Manifest State:")

    for key, expected in expected_state.items():
        actual = governance_state.get(key)

        if actual == expected:
            result = "PASS"
            detail = actual
        elif actual is None:
            result = "WARN"
            detail = "state not parsed"
        else:
            result = "WARN"
            detail = f"parsed={actual}, expected={expected}"

        print(
            f"[{result}] {key}: {detail}"
        )

        findings.append(
            Finding(
                "GOVERNANCE",
                result,
                key,
                detail,
            )
        )

    # =====================================================================
    # 3. Evidence inventory
    # =====================================================================

    print_section("3. PROJECT-OWNED EVIDENCE INVENTORY")

    docs = documentation_files()
    sources = source_files()
    tests = project_test_files()
    validators = validation_files()

    print(f"Documentation files       : {len(docs)}")
    print(f"Runtime source candidates : {len(sources)}")
    print(f"Project test candidates   : {len(tests)}")
    print(f"Validation tool files     : {len(validators)}")

    print()
    print("EXCLUDED FROM EVIDENCE:")
    print("  .venv/")
    print("  venv/")
    print("  node_modules/")
    print("  NOT_USABLE_DOCUMENTS/")
    print("  build/")
    print("  dist/")
    print("  generated/dependency trees")
    print("  .git/")

    # =====================================================================
    # 4. Boundary integrity
    # =====================================================================

    print_section("4. EVIDENCE BOUNDARY INTEGRITY")

    contamination_checks = {
        ".venv": any(
            ".venv/" in relative(path)
            for path in tests
        ),
        "NOT_USABLE_DOCUMENTS": any(
            relative(path).startswith(
                "NOT_USABLE_DOCUMENTS/"
            )
            for path in tests
        ),
        "node_modules": any(
            "node_modules/" in relative(path)
            for path in tests
        ),
        "build": any(
            relative(path).startswith("build/")
            for path in tests
        ),
        "dist": any(
            relative(path).startswith("dist/")
            for path in tests
        ),
    }

    for boundary, contaminated in contamination_checks.items():
        result = "FAIL" if contaminated else "PASS"

        print(
            f"[{result}] "
            f"{boundary} contamination = "
            f"{'YES' if contaminated else 'NO'}"
        )

        findings.append(
            Finding(
                "EVIDENCE_BOUNDARY",
                result,
                boundary,
                "contaminated" if contaminated else "clean",
            )
        )

    # =====================================================================
    # 5. Test inventory
    # =====================================================================

    print_section("5. PROJECT TEST INVENTORY")

    if not tests:
        print("[WARN] No project-owned tests discovered.")
    else:
        for path in tests:
            print(f"[TEST] {relative(path)}")

    # =====================================================================
    # 6. Validation tooling inventory
    # =====================================================================

    print_section("6. VALIDATION TOOLING")

    for path in validators:
        print(f"[VALIDATION] {relative(path)}")

    # =====================================================================
    # 7. Evidence matrix
    # =====================================================================

    print_section("7. PHASE-B EVIDENCE MATRIX")

    for profile in PROFILES:
        documentation_matches = matching_documentation_files(
            profile,
            docs,
        )

        source_matches = matching_source_files(
            profile,
            sources,
        )

        test_matches = matching_test_files(
            profile,
            tests,
        )

        validation_matches = matching_validation_files(
            profile,
            validators,
        )

        print()
        print(f"SLICE: {profile.name}")

        print(
            "  DOCUMENTED                       : "
            f"{'PRESENT' if documentation_matches else 'NOT FOUND'}"
        )

        print(
            "  RUNTIME_IMPLEMENTATION_PRESENT  : "
            f"{'PRESENT' if source_matches else 'NOT FOUND'}"
        )

        print(
            "  PROJECT_TESTS_PRESENT            : "
            f"{'PRESENT' if test_matches else 'NOT FOUND'}"
        )

        print(
            "  VALIDATION_TOOLING_PRESENT       : "
            f"{'PRESENT' if validation_matches else 'NOT FOUND'}"
        )

        print(
            "  EXECUTED_VALIDATION_EVIDENCE    : "
            "NOT ASSESSED BY FILE PRESENCE"
        )

        print(
            "  ACCEPTANCE_EVIDENCE              : "
            "NOT ASSESSED BY FILE PRESENCE"
        )

        if source_matches:
            print("  Runtime files:")
            for path in source_matches[:12]:
                print(f"    {relative(path)}")

        if test_matches:
            print("  Project test files:")
            for path in test_matches[:12]:
                print(f"    {relative(path)}")

        if validation_matches:
            print("  Validation tooling:")
            for path in validation_matches[:12]:
                print(f"    {relative(path)}")

        findings.append(
            Finding(
                "DOCUMENTATION",
                "PASS" if documentation_matches else "WARN",
                profile.name,
                f"{len(documentation_matches)} documentation files",
            )
        )

        findings.append(
            Finding(
                "RUNTIME_IMPLEMENTATION",
                "PASS" if source_matches else "WARN",
                profile.name,
                f"{len(source_matches)} runtime files",
            )
        )

        findings.append(
            Finding(
                "PROJECT_TESTS",
                "PASS" if test_matches else "WARN",
                profile.name,
                f"{len(test_matches)} project test files",
            )
        )

        findings.append(
            Finding(
                "VALIDATION_TOOLING",
                "PASS" if validation_matches else "WARN",
                profile.name,
                f"{len(validation_matches)} validation tools",
            )
        )

    # =====================================================================
    # 8. Critical evidence distinction
    # =====================================================================

    print_section("8. CRITICAL EVIDENCE DISTINCTION")

    print("FILE PRESENCE:")
    print("  Indicates that an artifact exists.")
    print("  Does NOT establish correctness.")

    print()
    print("TEST PRESENCE:")
    print("  Indicates project test source exists.")
    print("  Does NOT establish that tests passed.")

    print()
    print("VALIDATION TOOL PRESENCE:")
    print("  Indicates validation tooling exists.")
    print("  Does NOT establish successful validation.")

    print()
    print("EXECUTED VALIDATION:")
    print("  Requires actual execution records/evidence.")
    print("  This audit does NOT fabricate or infer such evidence.")

    print()
    print("ACCEPTANCE:")
    print("  Requires controlled acceptance evidence.")
    print("  This audit does NOT infer acceptance.")

    print()
    print("PRODUCTION CERTIFICATION:")
    print("  Governed separately.")
    print("  This audit makes no certification claim.")

    # =====================================================================
    # 9. Final decision
    # =====================================================================

    print_section("9. AUDIT DECISION")

    failures = [
        finding
        for finding in findings
        if finding.status == "FAIL"
    ]

    warnings = [
        finding
        for finding in findings
        if finding.status == "WARN"
    ]

    passes = [
        finding
        for finding in findings
        if finding.status == "PASS"
    ]

    if failures:
        decision = "BASELINE_AUDIT_BLOCKED"
    elif warnings:
        decision = "BASELINE_AUDIT_REQUIRES_REVIEW"
    else:
        decision = "BASELINE_AUDIT_COMPLETE"

    print(f"Decision : {decision}")
    print(f"PASS     : {len(passes)}")
    print(f"WARN     : {len(warnings)}")
    print(f"FAIL     : {len(failures)}")

    print()
    print("FAIL-CLOSED SAFETY BOUNDARY:")
    print("  Phase-B implementation       : NOT EXECUTED")
    print("  Runtime modification         : NONE")
    print("  Documentation modification   : NONE")
    print("  Manifest modification        : NONE")
    print("  Git mutation                 : NONE")
    print("  Production operation         : BLOCKED")
    print("  Production certification     : NOT CLAIMED")
    print("  G46.5/G47 reconstruction     : NOT PERFORMED")
    print("  R097 governance change       : NONE")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
