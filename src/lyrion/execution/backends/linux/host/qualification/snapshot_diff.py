from __future__ import annotations

from lyrion.execution.backends.linux.host.contracts import (
    HostPrimitive,
    HostPrimitiveCapability,
    LinuxHostAbstractionSnapshot,
)

from .change_contracts import ChangeImpact, HostChange


class LinuxHostSnapshotDiff:
    """
    Observational comparison of two LYRION Linux host snapshots.

    This component compares previously observed LYRION host state and
    produces deterministic HostChange records.

    It does not:
      - execute validation;
      - mutate the Linux host;
      - authorize execution;
      - apply enforcement;
      - alter system configuration.

    ChangeImpact values are LYRION project policy classifications.
    They are not claimed to be Linux, Debian, Ubuntu, or industry standards.
    """

    _SECURITY_PRIMITIVES = frozenset(
        {
            HostPrimitive.CGROUPS_V2,
            HostPrimitive.NAMESPACES,
            HostPrimitive.SECCOMP,
            HostPrimitive.NO_NEW_PRIVS,
            HostPrimitive.LANDLOCK,
            HostPrimitive.APPARMOR,
            HostPrimitive.LINUX_CAPABILITIES,
        }
    )

    _HOST_INTEGRATION_PRIMITIVES = frozenset(
        {
            HostPrimitive.SYSTEMD,
            HostPrimitive.BUBBLEWRAP,
            HostPrimitive.DOCKER,
            HostPrimitive.NFT,
            HostPrimitive.IPTABLES,
        }
    )

    def diff(
        self,
        *,
        previous: LinuxHostAbstractionSnapshot,
        current: LinuxHostAbstractionSnapshot,
    ) -> tuple[HostChange, ...]:
        changes: list[HostChange] = []

        self._compare_identity(previous, current, changes)
        self._compare_primitives(previous, current, changes)
        self._compare_execution_context(previous, current, changes)

        return tuple(
            sorted(
                changes,
                key=lambda change: (
                    change.component,
                    change.impact.value,
                    change.previous_value,
                    change.current_value,
                ),
            )
        )

    @staticmethod
    def _append(
        changes: list[HostChange],
        *,
        component: str,
        previous_value: str,
        current_value: str,
        impact: ChangeImpact,
        rationale: str,
    ) -> None:
        if previous_value == current_value:
            return

        changes.append(
            HostChange(
                component=component,
                previous_value=previous_value,
                current_value=current_value,
                impact=impact,
                rationale=rationale,
            )
        )

    def _compare_identity(
        self,
        previous: LinuxHostAbstractionSnapshot,
        current: LinuxHostAbstractionSnapshot,
        changes: list[HostChange],
    ) -> None:
        previous_identity = previous.identity
        current_identity = current.identity

        self._append(
            changes,
            component="host.identity.os_name",
            previous_value=previous_identity.os_name,
            current_value=current_identity.os_name,
            impact=ChangeImpact.CRITICAL,
            rationale=(
                "Linux distribution identity changed; full host "
                "qualification is required."
            ),
        )

        self._append(
            changes,
            component="host.identity.os_version",
            previous_value=previous_identity.os_version,
            current_value=current_identity.os_version,
            impact=ChangeImpact.CRITICAL,
            rationale=(
                "Reported Linux distribution version changed; the "
                "qualification baseline may no longer represent the host."
            ),
        )

        self._append(
            changes,
            component="host.identity.kernel",
            previous_value=previous_identity.kernel,
            current_value=current_identity.kernel,
            impact=ChangeImpact.HIGH,
            rationale=(
                "Kernel identity changed; Linux security and enforcement "
                "primitives require native security qualification."
            ),
        )

        self._append(
            changes,
            component="host.identity.architecture",
            previous_value=previous_identity.architecture,
            current_value=current_identity.architecture,
            impact=ChangeImpact.CRITICAL,
            rationale=(
                "CPU architecture changed; native execution and security "
                "qualification must be established for the new architecture."
            ),
        )

        self._append(
            changes,
            component="host.identity.virtualization",
            previous_value=str(previous_identity.virtualization),
            current_value=str(current_identity.virtualization),
            impact=ChangeImpact.CRITICAL,
            rationale=(
                "Virtualization environment changed; host enforcement "
                "assumptions must be requalified."
            ),
        )

        self._append(
            changes,
            component="host.identity.init_system",
            previous_value=str(previous_identity.init_system),
            current_value=str(current_identity.init_system),
            impact=ChangeImpact.MEDIUM,
            rationale=(
                "Observed init-system identity changed; affected host "
                "integration requires targeted regression."
            ),
        )

    def _compare_primitives(
        self,
        previous: LinuxHostAbstractionSnapshot,
        current: LinuxHostAbstractionSnapshot,
        changes: list[HostChange],
    ) -> None:
        previous_ids = set(previous.fingerprint.primitive_ids)
        current_ids = set(current.fingerprint.primitive_ids)

        for primitive_id in sorted(previous_ids | current_ids):
            primitive = HostPrimitive(primitive_id)

            previous_capability = self._capability_or_none(
                previous,
                primitive,
            )
            current_capability = self._capability_or_none(
                current,
                primitive,
            )

            if previous_capability is None:
                assert current_capability is not None
                self._append(
                    changes,
                    component=f"host.primitive.{primitive.value}",
                    previous_value="<missing>",
                    current_value=current_capability.state.value,
                    impact=ChangeImpact.HIGH,
                    rationale=(
                        "A previously unobserved Linux primitive is now "
                        "present; native security qualification is required."
                    ),
                )
                continue

            if current_capability is None:
                self._append(
                    changes,
                    component=f"host.primitive.{primitive.value}",
                    previous_value=previous_capability.state.value,
                    current_value="<missing>",
                    impact=ChangeImpact.HIGH,
                    rationale=(
                        "A previously observed Linux primitive is now "
                        "missing; native security qualification is required."
                    ),
                )
                continue

            impact = self._primitive_impact(primitive)

            self._append(
                changes,
                component=f"host.primitive.{primitive.value}.state",
                previous_value=previous_capability.state.value,
                current_value=current_capability.state.value,
                impact=impact,
                rationale=self._primitive_rationale(primitive),
            )

            previous_evidence = self._canonical_values(
                previous_capability.evidence,
            )
            current_evidence = self._canonical_values(
                current_capability.evidence,
            )

            self._append(
                changes,
                component=f"host.primitive.{primitive.value}.evidence",
                previous_value=previous_evidence,
                current_value=current_evidence,
                impact=impact,
                rationale=(
                    "Observed primitive evidence changed; the affected "
                    "host capability requires requalification."
                ),
            )

    def _compare_execution_context(
        self,
        previous: LinuxHostAbstractionSnapshot,
        current: LinuxHostAbstractionSnapshot,
        changes: list[HostChange],
    ) -> None:
        self._append(
            changes,
            component="host.user_id",
            previous_value=str(previous.user_id),
            current_value=str(current.user_id),
            impact=ChangeImpact.MEDIUM,
            rationale=(
                "Observed execution user changed; privilege-sensitive "
                "integration requires targeted regression."
            ),
        )

        self._append(
            changes,
            component="host.effective_capabilities",
            previous_value=self._canonical_values(
                previous.effective_capabilities,
            ),
            current_value=self._canonical_values(
                current.effective_capabilities,
            ),
            impact=ChangeImpact.HIGH,
            rationale=(
                "Effective Linux capabilities changed; privilege-sensitive "
                "security qualification is required."
            ),
        )

        self._append(
            changes,
            component="host.namespaces",
            previous_value=self._canonical_values(previous.namespaces),
            current_value=self._canonical_values(current.namespaces),
            impact=ChangeImpact.HIGH,
            rationale=(
                "Observed namespace set changed; namespace isolation "
                "requires native security qualification."
            ),
        )

    @staticmethod
    def _capability_or_none(
        snapshot: LinuxHostAbstractionSnapshot,
        primitive: HostPrimitive,
    ) -> HostPrimitiveCapability | None:
        try:
            return snapshot.capability(primitive)
        except KeyError:
            return None

    @classmethod
    def _primitive_impact(
        cls,
        primitive: HostPrimitive,
    ) -> ChangeImpact:
        if primitive in cls._SECURITY_PRIMITIVES:
            return ChangeImpact.HIGH

        if primitive in cls._HOST_INTEGRATION_PRIMITIVES:
            return ChangeImpact.MEDIUM

        return ChangeImpact.MEDIUM

    @classmethod
    def _primitive_rationale(
        cls,
        primitive: HostPrimitive,
    ) -> str:
        if primitive in cls._SECURITY_PRIMITIVES:
            return (
                "Observed security-relevant Linux primitive state changed; "
                "native security qualification is required."
            )

        return (
            "Observed host integration primitive state changed; "
            "targeted regression is required."
        )

    @staticmethod
    def _canonical_values(values: tuple[str, ...]) -> str:
        return ",".join(sorted(values))
