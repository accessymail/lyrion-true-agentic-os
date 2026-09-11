"""Native Linux seccomp enforcement tests using disposable child processes."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from lyrion.execution.backends.linux.enforcement.primitives.no_new_privs import (
    LibcNoNewPrivsOperations,
)
from lyrion.execution.backends.linux.enforcement.primitives.seccomp import (
    NativeSeccompOperations,
)
from lyrion.execution.backends.linux.enforcement.seccomp_policy import (
    SeccompArchitecture,
    SeccompDefaultAction,
    SeccompPolicy,
)

PROJECT_ROOT = Path(__file__).resolve().parents[6]


def _errno_policy() -> SeccompPolicy:
    """Return a deliberately small native test policy.

    The policy permits the syscalls needed after installation to communicate
    the result and terminate normally.  getpid is intentionally omitted and
    therefore must receive EPERM from the ERRNO default action.
    """
    return SeccompPolicy(
        policy_id="LYRION-NATIVE-R3-R2-ERRNO",
        policy_version="1.0.0",
        architecture=SeccompArchitecture.X86_64,
        default_action=SeccompDefaultAction.ERRNO,
        allowed_syscalls=(
            "close",
            "exit",
            "exit_group",
            "write",
        ),
    )


def _kill_policy() -> SeccompPolicy:
    """Return a policy whose default action terminates the child."""
    return SeccompPolicy(
        policy_id="LYRION-NATIVE-R3-R2-KILL",
        policy_version="1.0.0",
        architecture=SeccompArchitecture.X86_64,
        default_action=SeccompDefaultAction.KILL_PROCESS,
        allowed_syscalls=(
            "close",
            "exit",
            "exit_group",
            "write",
        ),
    )


def _child_code(policy_kind: str, fd: int) -> str:
    """Build the isolated child program."""
    return f"""
import ctypes
import errno
import os
import sys

sys.path.insert(0, {str(PROJECT_ROOT)!r})

from lyrion.execution.backends.linux.enforcement.primitives.no_new_privs import (
    LibcNoNewPrivsOperations,
)
from lyrion.execution.backends.linux.enforcement.primitives.seccomp import (
    NativeSeccompOperations,
)
from lyrion.execution.backends.linux.enforcement.seccomp_policy import (
    SeccompArchitecture,
    SeccompDefaultAction,
    SeccompPolicy,
)

fd = {fd}
policy_kind = {policy_kind!r}

if policy_kind == "errno":
    policy = SeccompPolicy(
        policy_id="LYRION-NATIVE-R3-R2-ERRNO",
        policy_version="1.0.0",
        architecture=SeccompArchitecture.X86_64,
        default_action=SeccompDefaultAction.ERRNO,
        allowed_syscalls=(
            "close",
            "exit",
            "exit_group",
            "write",
        ),
    )
elif policy_kind == "kill":
    policy = SeccompPolicy(
        policy_id="LYRION-NATIVE-R3-R2-KILL",
        policy_version="1.0.0",
        architecture=SeccompArchitecture.X86_64,
        default_action=SeccompDefaultAction.KILL_PROCESS,
        allowed_syscalls=(
            "close",
            "exit",
            "exit_group",
            "write",
        ),
    )
else:
    raise RuntimeError("unknown policy kind")

LibcNoNewPrivsOperations().set_no_new_privs()

operations = NativeSeccompOperations()
operations.install_policy(policy)

if policy_kind == "errno":
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long

    # x86_64 Linux: SYS_getpid = 39.
    ctypes.set_errno(0)
    result = libc.syscall(39)
    error_number = ctypes.get_errno()

    if result != -1 or error_number != errno.EPERM:
        os.write(
            fd,
            b"FAIL: prohibited getpid syscall was not denied",
        )
        os._exit(10)

    os.write(
        fd,
        b"PASS: native seccomp denied prohibited syscall",
    )
    os._exit(0)

# For KILL_PROCESS the following getpid() must never complete.
libc = ctypes.CDLL(None, use_errno=True)
libc.syscall.restype = ctypes.c_long

# x86_64 Linux: SYS_getpid = 39.
libc.syscall(39)
os.write(fd, b"FAIL: kill policy did not terminate syscall")
os._exit(11)
"""


def _run_child(
    policy_kind: str,
) -> tuple[subprocess.CompletedProcess[bytes], bytes]:
    """Execute the native filter inside a disposable subprocess."""
    read_fd, write_fd = os.pipe()

    try:
        code = _child_code(policy_kind, write_fd)

        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                code,
            ],
            cwd=PROJECT_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            pass_fds=(write_fd,),
        )

        # The parent must close its copy immediately.  Otherwise the read
        # side cannot observe EOF after the child exits.
        os.close(write_fd)

        stdout, stderr = process.communicate(timeout=10)
        evidence = os.read(read_fd, 4096)

        result = subprocess.CompletedProcess(
            process.args,
            process.returncode,
            stdout,
            stderr,
        )

        return result, evidence

    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise
    finally:
        try:
            os.close(read_fd)
        except OSError:
            pass


def test_native_no_new_privs_can_be_established_in_child() -> None:
    """Verify the prerequisite independently in a disposable child."""
    read_fd, write_fd = os.pipe()

    code = f"""
import os
import sys

sys.path.insert(0, {str(PROJECT_ROOT)!r})

from lyrion.execution.backends.linux.enforcement.primitives.no_new_privs import (
    LibcNoNewPrivsOperations,
)

operations = LibcNoNewPrivsOperations()
operations.set_no_new_privs()

if not operations.get_no_new_privs():
    os.write({write_fd}, b"FAIL")
    os._exit(1)

os.write({write_fd}, b"PASS")
os._exit(0)
"""

    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=PROJECT_ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            pass_fds=(write_fd,),
            timeout=10,
            check=False,
        )

        evidence = os.read(read_fd, 64)

        assert result.returncode == 0, (
            result.stderr.decode(errors="replace")
        )
        assert evidence == b"PASS"
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_native_errno_policy_denies_prohibited_syscall() -> None:
    """Prove that the kernel enforces the native ERRNO policy."""
    result, evidence = _run_child("errno")

    assert result.returncode == 0, (
        "child failed unexpectedly: "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert evidence == b"PASS: native seccomp denied prohibited syscall"


def test_native_kill_policy_terminates_prohibited_syscall() -> None:
    """Prove that KILL_PROCESS terminates the disposable child."""
    result, evidence = _run_child("kill")

    assert result.returncode < 0, (
        "KILL_PROCESS child unexpectedly exited normally: "
        f"returncode={result.returncode}, "
        f"stdout={result.stdout!r}, "
        f"stderr={result.stderr!r}"
    )
    assert evidence == b""


def test_parent_kernel_state_is_unchanged_after_child_tests() -> None:
    """Ensure native child enforcement does not mutate the test parent."""
    operations = NativeSeccompOperations()
    state = operations.get_state()

    assert state.architecture == "x86_64"
    assert state.installed is False
    assert LibcNoNewPrivsOperations().get_no_new_privs() is False
