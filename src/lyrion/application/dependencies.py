"""Centralized Application Runtime dependency construction."""

from __future__ import annotations

from lyrion.application.runtime import ApplicationRuntime


def build_application_runtime() -> ApplicationRuntime:
    """Construct the application orchestration boundary."""

    return ApplicationRuntime()
