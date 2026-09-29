#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/aniket/lyrion-migration-verified")
EXPECTED_HEAD = "7b1f7fd676d32194748d8ba4f603a42edb3cf4cc"

TARGET_TRACKED = {
    "Manifest.md",
    "docs/Manifest.md",
    "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
    "docs/phase-b/execution-admission/"
    "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md",
}

EXPECTED_UNTRACKED_PREFIXES = {
    "docs/phase-b/validation/"
    "EXECUTION_ADMISSION_SLICE_ACCEPTANCE_RECORD_v1.md",
    "tools/phase_b/audit/",
    "execution_admission_",
    "review_execution_admission_",
    "validate_execution_admission_",
    "plan_execution_admission_",
    "discover_execution_admission_",
    "inspect_execution_admission_",
}

FORBIDDEN_PATH_PREFIXES = (
    "src/",
    "tests/",
)

FORBIDDEN_CLAIMS = (
    "PRODUCTION CERTIFIED",
    "PRODUCTION_CERTIFIED",
    "G46.5 CLOSED",
    "G47 CLOSED",
    "G47_CLOSED",
    "R097 MODIFIED",
    "R097_MODIFICATION PERFORMED",
)

RUNTIME_FILES = {
    "src/lyrion/capabilities/gateway.py":
        "a7ce8f4a00e54f137d559c8c13e9026e50d1b3eafbd8bc3d1029c90d35f19fa9",
    "src/lyrion/execution/contracts.py":
        "ca8af0c9e94789b7e561fc43a32e037c7c1d8aade1eaa73985f3118c7c40def2",
    "src/lyrion/execution/validator.py":
        "1a39ac52d29d2ab27bcfac9788a0aae1b0ddcc85d5ba7105790793a866ad69a8",
    "src/lyrion/execution/executor.py":
        "8c1687dda5defc35d439264ad824de92a8aa20726e144f809b330b90c26efd05",
}


def run(*args: str) -> str:
    result = subprocess.run(
        args,
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(args)}\n"
            f"{result.stdout}"
        )
    return result.stdout


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def status_paths() -> list[str]:
    output = run("git", "status", "--short", "--untracked-files=all")
    paths: list[str] = []

    for line in output.splitlines():
        if not line:
            continue

        # git status --short:
        # XY path
        # For rename/copy records, retain the complete line for safety.
        if len(line) < 4:
            raise AssertionError(f"Malformed git status line: {line!r}")

        paths.append(line[3:])

    return paths


def main() -> int:
    os.environ["LC_ALL"] = "C"

    passed = 0
    failed = 0
    warnings = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"[PASS] {name}")
            if detail:
                print(f"       {detail}")
        else:
            failed += 1
            print(f"[FAIL] {name}")
            if detail:
                print(f"       {detail}")

    def warn(name: str, detail: str) -> None:
        nonlocal warnings
        warnings += 1
        print(f"[WARN] {name}")
        print(f"       {detail}")

    print("=" * 76)
    print("LYRION EXECUTION ADMISSION DOCUMENTATION DIFF REVIEW")
    print("=" * 76)

    # ------------------------------------------------------------------
    # Repository baseline
    # ------------------------------------------------------------------
    head = run("git", "rev-parse", "HEAD").strip()
    origin = run("git", "rev-parse", "origin/main").strip()

    check(
        "Repository HEAD matches expected validated baseline",
        head == EXPECTED_HEAD,
        f"HEAD={head}",
    )

    check(
        "Repository HEAD equals origin/main",
        head == origin,
        f"origin/main={origin}",
    )

    # ------------------------------------------------------------------
    # Status inventory
    # ------------------------------------------------------------------
    raw_status = run(
        "git",
        "status",
        "--short",
        "--untracked-files=all",
    )

    print("\n--- CURRENT GIT STATUS ---")
    print(raw_status.rstrip() or "(clean)")

    paths = status_paths()

    modified_tracked = []
    untracked = []

    for line in raw_status.splitlines():
        if not line:
            continue

        xy = line[:2]
        path = line[3:]

        if xy == "??":
            untracked.append(path)
        else:
            modified_tracked.append(path)

    check(
        "No runtime source or project-test files are modified",
        not any(
            p.startswith(FORBIDDEN_PATH_PREFIXES)
            for p in modified_tracked
        ),
        "src/ and tests/ must remain untouched",
    )

    # ------------------------------------------------------------------
    # Exact tracked documentation scope
    # ------------------------------------------------------------------
    unexpected_tracked = sorted(
        set(modified_tracked) - TARGET_TRACKED
    )

    check(
        "Modified tracked files are limited to approved documentation targets",
        not unexpected_tracked,
        "Unexpected tracked paths: "
        + (", ".join(unexpected_tracked) if unexpected_tracked else "none"),
    )

    for target in sorted(TARGET_TRACKED):
        check(
            f"Expected tracked target present: {target}",
            target in modified_tracked,
        )

    # ------------------------------------------------------------------
    # Untracked artifact scope
    # ------------------------------------------------------------------
    unexpected_untracked = []

    for path in untracked:
        normalized_path = path.strip('"')

        if normalized_path.startswith(
            "NOT_USABLE_DOCUMENTS/Don't use/"
        ):
            continue

        if (
            path.startswith("docs/phase-b/validation/")
            or path.startswith("tools/phase_b/audit/")
        ):
            continue

        unexpected_untracked.append(path)

    check(
        "Untracked artifacts remain within approved validation/documentation scope",
        not unexpected_untracked,
        "Unexpected untracked paths: "
        + (", ".join(sorted(unexpected_untracked))
           if unexpected_untracked else "none"),
    )

    # ------------------------------------------------------------------
    # Diff inventory
    # ------------------------------------------------------------------
    diff_name_status = run("git", "diff", "--name-status")
    diff_stat = run("git", "diff", "--stat")

    print("\n--- TRACKED DIFF NAME STATUS ---")
    print(diff_name_status.rstrip() or "(none)")

    print("\n--- TRACKED DIFF STAT ---")
    print(diff_stat.rstrip() or "(none)")

    diff_text = run("git", "diff", "--no-ext-diff", "--unified=0")

    check(
        "Tracked diff contains no runtime source/test paths",
        not any(
            p in diff_text
            for p in (
                "+++ b/src/",
                "--- a/src/",
                "+++ b/tests/",
                "--- a/tests/",
            )
        ),
    )

    # ------------------------------------------------------------------
    # Protected claims
    # ------------------------------------------------------------------
    upper_diff = diff_text.upper()

    prohibited_found = [
        claim for claim in FORBIDDEN_CLAIMS
        if claim in upper_diff
    ]

    check(
        "Tracked diff introduces no prohibited certification/reconstruction claims",
        not prohibited_found,
        "Detected: "
        + (", ".join(prohibited_found) if prohibited_found else "none"),
    )

    # ------------------------------------------------------------------
    # Runtime integrity
    # ------------------------------------------------------------------
    print("\n--- RUNTIME SHA-256 INTEGRITY ---")

    runtime_ok = True

    for relative, expected in RUNTIME_FILES.items():
        path = REPO / relative

        if not path.is_file():
            runtime_ok = False
            print(f"[FAIL] Missing runtime file: {relative}")
            continue

        actual = sha256(path)
        same = actual == expected

        if same:
            print(f"[PASS] {relative}")
            print(f"       SHA-256: {actual}")
        else:
            runtime_ok = False
            print(f"[FAIL] {relative}")
            print(f"       expected: {expected}")
            print(f"       actual  : {actual}")

    check(
        "All four reviewed runtime files retain accepted SHA-256",
        runtime_ok,
    )

    # ------------------------------------------------------------------
    # Project manifest synchronization
    # ------------------------------------------------------------------
    manifest_a = REPO / "Manifest.md"
    manifest_b = REPO / "docs/Manifest.md"

    manifests_ok = (
        manifest_a.is_file()
        and manifest_b.is_file()
        and manifest_a.read_bytes() == manifest_b.read_bytes()
    )

    check(
        "Project manifests remain byte-identical",
        manifests_ok,
    )

    if manifests_ok:
        print(
            f"       SHA-256: {sha256(manifest_a)}"
        )

    # ------------------------------------------------------------------
    # Acceptance record existence and bounded semantics
    # ------------------------------------------------------------------
    acceptance = (
        REPO
        / "docs/phase-b/validation/"
        / "EXECUTION_ADMISSION_SLICE_ACCEPTANCE_RECORD_v1.md"
    )

    check(
        "Execution Admission bounded-slice acceptance record exists",
        acceptance.is_file(),
    )

    if acceptance.is_file():
        text = acceptance.read_text(encoding="utf-8")
        lowered = text.lower()

        required_phrases = (
            "execution_admission_slice_accepted",
            "full pb-doc-009 validation remains distinct",
            "production certification: not claimed",
            "g46.5",
            "g47",
            "r097",
        )

        for phrase in required_phrases:
            check(
                f"Acceptance record contains required bounded-state phrase: {phrase}",
                phrase in lowered,
            )

        if "production certified" in lowered:
            failed += 1
            print(
                "[FAIL] Acceptance record contains prohibited "
                "production-certification wording"
            )
        else:
            passed += 1
            print(
                "[PASS] Acceptance record contains no "
                "production-certification claim"
            )

    # ------------------------------------------------------------------
    # Backup preservation
    # ------------------------------------------------------------------
    backup_root = (
        REPO
        / "NOT_USABLE_DOCUMENTS"
        / "Don't use"
        / "PHASE_B_DOCUMENTATION_SYNC_BACKUPS"
    )

    check(
        "Documentation synchronization backup root exists",
        backup_root.is_dir(),
    )

    if backup_root.is_dir():
        backup_dirs = sorted(
            p for p in backup_root.iterdir()
            if p.is_dir()
        )

        check(
            "At least one synchronization backup set exists",
            bool(backup_dirs),
        )

        if backup_dirs:
            latest = backup_dirs[-1]
            backup_files = sorted(
                p.relative_to(latest).as_posix()
                for p in latest.rglob("*")
                if p.is_file()
            )

            print(
                f"       Latest backup set: {latest.relative_to(REPO)}"
            )
            print(
                f"       Files preserved: {len(backup_files)}"
            )

            check(
                "Latest backup set preserves four synchronized target documents",
                len(backup_files) >= 4,
                ", ".join(backup_files),
            )

    # ------------------------------------------------------------------
    # Synchronization report
    # ------------------------------------------------------------------
    report = (
        REPO
        / "tools/phase_b/audit/"
        / "execution_admission_documentation_sync_report.json"
    )

    check(
        "Documentation synchronization report exists",
        report.is_file(),
    )

    if report.is_file():
        try:
            data = json.loads(report.read_text(encoding="utf-8"))

            expected_fields = {
                "decision": "DOCUMENTATION_SYNC_VALIDATED_PENDING_REVIEW",
                "runtime_integrity": "UNCHANGED",
                "project_manifests": "BYTE_IDENTICAL",
                "production_certification": "NOT_CLAIMED",
                "g46_5_reconstruction": "NOT_PERFORMED",
                "g47_reconstruction": "NOT_PERFORMED",
                "r097_modification": "NOT_PERFORMED",
                "git_commit": "NOT_PERFORMED",
                "git_push": "NOT_PERFORMED",
            }

            for key, expected in expected_fields.items():
                actual = data.get(key)
                check(
                    f"Sync report field {key}={expected}",
                    actual == expected,
                    f"actual={actual!r}",
                )

        except (OSError, json.JSONDecodeError) as exc:
            check(
                "Synchronization report is valid JSON",
                False,
                str(exc),
            )

    # ------------------------------------------------------------------
    # Diff-level sanity review
    # ------------------------------------------------------------------
    print("\n--- DIFF-LEVEL SANITY ---")

    if diff_text:
        added_lines = [
            line[1:]
            for line in diff_text.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]

        suspicious_terms = (
            "authorized all phase b",
            "production implementation authorized",
            "production certification achieved",
            "g47 closed",
            "g46.5 closed",
            "self-learning enabled",
            "self-evolution enabled",
        )

        suspicious = [
            term
            for term in suspicious_terms
            if any(term in line.lower() for line in added_lines)
        ]

        if suspicious:
            check(
                "No broad authorization/certification/self-evolution claims added",
                False,
                ", ".join(suspicious),
            )
        else:
            check(
                "No broad authorization/certification/self-evolution claims added",
                True,
            )

    # ------------------------------------------------------------------
    # Final decision
    # ------------------------------------------------------------------
    print("\n" + "=" * 76)
    print("FINAL DIFF REVIEW")
    print("=" * 76)
    print(f"PASS : {passed}")
    print(f"WARN : {warnings}")
    print(f"FAIL : {failed}")

    if failed:
        decision = "DOCUMENTATION_DIFF_REVIEW_FAILED"
        rc = 1
    else:
        decision = "DOCUMENTATION_DIFF_REVIEW_PASSED_PENDING_COMMIT"
        rc = 0

    print(f"DECISION: {decision}")
    print("=" * 76)

    print(
        "Commit/push remains prohibited until this review passes "
        "and the commit scope is explicitly approved."
    )

    return rc


if __name__ == "__main__":
    import os

    sys.exit(main())
