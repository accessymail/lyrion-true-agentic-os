from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LinuxHostCapabilitySnapshot:
    """
    Read-only description of the Linux host's relevant security primitives.

    Support, availability, and enforcement readiness are intentionally
    represented separately. Kernel support alone is never treated as proof
    that a mechanism can be enforced by LYRION.
    """

    os_name: str
    os_version: str
    kernel: str
    architecture: str
    virtualization: str | None

    cgroup_version: str | None
    namespaces: tuple[str, ...]

    seccomp_kernel_supported: bool
    landlock_kernel_supported: bool

    apparmor_kernel_supported: bool
    apparmor_active: bool

    no_new_privs_available: bool
    no_new_privs_active: bool

    systemd_available: bool
    bubblewrap_available: bool
    docker_available: bool
    nft_available: bool
    iptables_available: bool

    user_id: int
    effective_capabilities: tuple[str, ...]

    notes: tuple[str, ...]


def _command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def _read_os_release() -> tuple[str, str]:
    values: dict[str, str] = {}

    text = _read_text(Path("/etc/os-release"))
    if text:
        for line in text.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')

    return values.get("NAME", platform.system()), values.get(
        "VERSION_ID", platform.release()
    )


def _kernel_config_contains(option: str) -> bool:
    candidates = (
        Path("/proc/config.gz"),
        Path(f"/boot/config-{platform.release()}"),
    )

    for path in candidates:
        if path == Path("/proc/config.gz"):
            try:
                import gzip

                with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
            except OSError:
                continue
        else:
            text = _read_text(path) or ""

        if f"{option}=y" in text or f"{option}=m" in text:
            return True

    return False


def _detect_namespaces() -> tuple[str, ...]:
    namespace_dir = Path("/proc/self/ns")

    try:
        return tuple(sorted(item.name for item in namespace_dir.iterdir()))
    except OSError:
        return ()


def _detect_cgroup_version() -> str | None:
    if Path("/sys/fs/cgroup/cgroup.controllers").exists():
        return "v2"

    if Path("/sys/fs/cgroup").exists():
        return "unknown"

    return None


def _detect_apparmor_active() -> bool:
    securityfs = Path("/sys/kernel/security/apparmor")
    if not securityfs.exists():
        return False

    try:
        text = _read_text(securityfs / "profiles")
        return bool(text)
    except OSError:
        return False


def _detect_no_new_privs() -> tuple[bool, bool]:
    status = _read_text(Path("/proc/self/status"))
    if not status:
        return False, False

    value: int | None = None

    for line in status.splitlines():
        if line.startswith("NoNewPrivs:"):
            try:
                value = int(line.split(":", 1)[1].strip())
            except ValueError:
                value = None
            break

    return value is not None, value == 1


def _detect_effective_capabilities() -> tuple[str, ...]:
    status = _read_text(Path("/proc/self/status"))
    if not status:
        return ()

    for line in status.splitlines():
        if not line.startswith("CapEff:"):
            continue

        try:
            value = int(line.split(":", 1)[1].strip(), 16)
        except ValueError:
            return ()

        if value == 0:
            return ()

        return (f"0x{value:x}",)

    return ()


class LinuxHostCapabilityDetector:
    """Read-only Linux host capability detector."""

    def detect(self) -> LinuxHostCapabilitySnapshot:
        os_name, os_version = _read_os_release()

        seccomp_supported = _kernel_config_contains("CONFIG_SECCOMP")
        landlock_supported = _kernel_config_contains("CONFIG_LANDLOCK")
        apparmor_supported = _kernel_config_contains("CONFIG_SECURITY_APPARMOR")

        no_new_privs_available, no_new_privs_active = _detect_no_new_privs()

        virtualization: str | None = None
        if _command_exists("systemd-detect-virt"):
            try:
                result = subprocess.run(
                    ["systemd-detect-virt"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=2,
                )
                candidate = result.stdout.strip()
                virtualization = candidate or None
            except (OSError, subprocess.SubprocessError):
                virtualization = None

        notes: list[str] = []

        if virtualization == "wsl":
            notes.append(
                "WSL2 detected: native Linux production enforcement is not established."
            )

        if apparmor_supported and not _detect_apparmor_active():
            notes.append("AppArmor kernel support exists but AppArmor is not active.")

        if not seccomp_supported:
            notes.append("Kernel seccomp support was not established.")

        if not landlock_supported:
            notes.append("Kernel Landlock support was not established.")

        if _detect_cgroup_version() != "v2":
            notes.append("cgroup v2 was not established.")

        return LinuxHostCapabilitySnapshot(
            os_name=os_name,
            os_version=os_version,
            kernel=platform.release(),
            architecture=platform.machine(),
            virtualization=virtualization,
            cgroup_version=_detect_cgroup_version(),
            namespaces=_detect_namespaces(),
            seccomp_kernel_supported=seccomp_supported,
            landlock_kernel_supported=landlock_supported,
            apparmor_kernel_supported=apparmor_supported,
            apparmor_active=_detect_apparmor_active(),
            no_new_privs_available=no_new_privs_available,
            no_new_privs_active=no_new_privs_active,
            systemd_available=_command_exists("systemctl"),
            bubblewrap_available=_command_exists("bwrap"),
            docker_available=_command_exists("docker"),
            nft_available=_command_exists("nft"),
            iptables_available=_command_exists("iptables"),
            user_id=os.getuid(),
            effective_capabilities=_detect_effective_capabilities(),
            notes=tuple(notes),
        )


class LinuxHostCapabilityProvider:
    """Dependency-injectable provider for Linux host capability detection."""

    def __init__(self, detector: LinuxHostCapabilityDetector | None = None) -> None:
        self._detector = detector or LinuxHostCapabilityDetector()

    def snapshot(self) -> LinuxHostCapabilitySnapshot:
        return self._detector.detect()
