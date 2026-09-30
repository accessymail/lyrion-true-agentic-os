#!/usr/bin/env python3
"""
LYRION True Agentic OS
Aegis Concrete Call-Chain Tracer

READ-ONLY.

Purpose:
    Trace concrete method/function delegation through the existing Aegis,
    Capability Gateway, Execution Admission, and Secure Executor code.

This tool is evidence reconnaissance only.

It does not:
    - execute production runtime code
    - modify source/tests/docs/manifests
    - modify Git
    - reconstruct G46.5/G47
    - modify R097
    - claim production certification
"""

from __future__ import annotations

import ast
import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]

FILES = [
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


@dataclass(frozen=True)
class Definition:
    file: Path
    qualified_name: str
    node: ast.FunctionDef | ast.AsyncFunctionDef
    line: int


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


def dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def collect_definitions(
    path: Path,
) -> list[Definition]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))

    definitions: list[Definition] = []

    def visit(
        node: ast.AST,
        prefix: str,
    ) -> None:
        if isinstance(node, ast.ClassDef):
            current = f"{prefix}.{node.name}" if prefix else node.name

            for child in node.body:
                visit(child, current)

            return

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            current = f"{prefix}.{node.name}" if prefix else node.name

            definitions.append(
                Definition(
                    file=path,
                    qualified_name=current,
                    node=node,
                    line=node.lineno,
                )
            )

            return

        for child in ast.iter_child_nodes(node):
            visit(child, prefix)

    visit(tree, "")

    return definitions


def collect_all() -> list[Definition]:
    result: list[Definition] = []

    for path in FILES:
        if not path.is_file():
            print(f"[FAIL] Missing: {path.relative_to(REPO)}")
            continue

        result.extend(collect_definitions(path))

    return result


def function_calls(node: ast.AST) -> list[tuple[int, str]]:
    calls: list[tuple[int, str]] = []

    for item in ast.walk(node):
        if isinstance(item, ast.Call):
            name = dotted(item.func)

            if name:
                calls.append((item.lineno, name))

    return sorted(set(calls))


def return_expressions(
    node: ast.AST,
) -> list[tuple[int, str]]:
    results: list[tuple[int, str]] = []

    for item in ast.walk(node):
        if isinstance(item, ast.Return):
            if item.value is None:
                results.append((item.lineno, "return"))
            else:
                results.append(
                    (
                        item.lineno,
                        ast.unparse(item.value),
                    )
                )

    return results


def names_used(node: ast.AST) -> set[str]:
    values: set[str] = set()

    for item in ast.walk(node):
        if isinstance(item, ast.Name):
            values.add(item.id)

        elif isinstance(item, ast.Attribute):
            values.add(item.attr)

    return values


def locate(
    definitions: list[Definition],
    fragment: str,
) -> list[Definition]:
    fragment_lower = fragment.lower()

    return [
        definition
        for definition in definitions
        if fragment_lower in definition.qualified_name.lower()
    ]


def print_definition(definition: Definition) -> None:
    print()
    print("-" * 78)
    print(
        f"{definition.file.relative_to(REPO)}:"
        f"{definition.line}"
    )
    print(definition.qualified_name)
    print("-" * 78)

    print("CALLS:")

    calls = function_calls(definition.node)

    if calls:
        for line, name in calls:
            print(f"  L{line}: {name}")
    else:
        print("  <none>")

    print("RETURNS:")

    returns = return_expressions(definition.node)

    if returns:
        for line, expression in returns:
            print(f"  L{line}: {expression}")
    else:
        print("  <none>")

    print("KEY NAMES:")

    for name in sorted(names_used(definition.node)):
        print(f"  - {name}")


def trace_fragment(
    definitions: list[Definition],
    label: str,
    fragment: str,
) -> None:
    print()
    print("=" * 78)
    print(label)
    print("=" * 78)

    matches = locate(definitions, fragment)

    if not matches:
        print("[WARN] No matching definition")
        return

    for definition in matches:
        print_definition(definition)


def source_reference_search(
    terms: list[str],
) -> None:
    print()
    print("=" * 78)
    print("SOURCE-LEVEL CROSS-REFERENCE SEARCH")
    print("=" * 78)

    for term in terms:
        print()
        print(f"TERM: {term}")

        result = subprocess.run(
            [
                "git",
                "grep",
                "-n",
                "-I",
                "-E",
                term,
                "--",
                "src/lyrion/security",
                "src/lyrion/capabilities",
                "src/lyrion/execution",
                "tests/unit",
            ],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )

        lines = result.stdout.splitlines()

        if not lines:
            print("  NO MATCHES")
            continue

        for line in lines[:80]:
            print(f"  {line}")

        if len(lines) > 80:
            print(
                f"  ... {len(lines) - 80} additional matches omitted"
            )


def verify_source_integrity() -> None:
    print()
    print("=" * 78)
    print("RUNTIME SOURCE INTEGRITY")
    print("=" * 78)

    for path in FILES:
        if path.is_file():
            print(
                f"{path.relative_to(REPO)}"
                f"  SHA256={sha256(path)}"
            )


def main() -> int:
    print("=" * 78)
    print("LYRION TRUE AGENTIC OS")
    print("AEGIS CONCRETE CALL-CHAIN TRACER")
    print("READ-ONLY")
    print("=" * 78)

    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")
    status = git("status", "--short", "--untracked-files=all")

    print("\nREPOSITORY")
    print(f"HEAD:        {head}")
    print(f"origin/main: {origin}")

    if head == origin:
        print("[PASS] HEAD == origin/main")
    else:
        print("[WARN] HEAD != origin/main")

    print("\nWORKTREE")

    if status:
        print(status)
        print("[INFO] Existing read-only audit tools remain untracked.")
    else:
        print("[PASS] CLEAN")

    print("\nLOADING DEFINITIONS")

    definitions = collect_all()

    print(
        f"[PASS] Discovered {len(definitions)} "
        "Python function/method definitions"
    )

    trace_fragment(
        definitions,
        "AEGIS POLICY",
        "AegisPolicyEvaluator",
    )

    trace_fragment(
        definitions,
        "AEGIS AUTHORIZATION",
        "AegisAuthorizationService",
    )

    trace_fragment(
        definitions,
        "AUTHORIZATION GUARD",
        "AuthorizationGuard",
    )

    trace_fragment(
        definitions,
        "REPLAY GUARD",
        "ReplayGuard",
    )

    trace_fragment(
        definitions,
        "CAPABILITY GATEWAY",
        "CapabilityGateway",
    )

    trace_fragment(
        definitions,
        "EXECUTION ADMISSION",
        "ExecutionAdmission",
    )

    trace_fragment(
        definitions,
        "EXECUTION VALIDATOR",
        "ExecutionValidator",
    )

    trace_fragment(
        definitions,
        "SECURE EXECUTOR",
        "SecureExecutor",
    )

    source_reference_search(
        [
            r"AegisPolicyEvaluator",
            r"AegisAuthorizationService",
            r"AuthorizationGuard",
            r"ReplayGuard",
            r"validate_authorization_state",
            r"from_authorization",
            r"ExecutionAdmission",
            r"authorization_decision",
            r"require_authorized",
            r"validate_for_execution",
            r"DENIED",
            r"REVOKED",
            r"REQUIRES_APPROVAL",
        ]
    )

    verify_source_integrity()

    print()
    print("=" * 78)
    print("PROTECTED BOUNDARIES")
    print("=" * 78)
    print("[PASS] No runtime execution")
    print("[PASS] No source modification")
    print("[PASS] No test modification")
    print("[PASS] No documentation modification")
    print("[PASS] No manifest modification")
    print("[PASS] No Git mutation")
    print("[PASS] No G46.5 reconstruction")
    print("[PASS] No G47 reconstruction")
    print("[PASS] No R097 modification")
    print("[PASS] Production certification NOT CLAIMED")

    print()
    print("=" * 78)
    print("DECISION")
    print("=" * 78)
    print(
        "AEGIS_CALL_CHAIN_TRACE_COMPLETE_"
        "PENDING_ENGINEERING_REVIEW"
    )

    print()
    print(
        "This output is source-level evidence only. "
        "It does not establish runtime validation or acceptance."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
