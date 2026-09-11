"""Opt-in live integration test for the Gemini-backed Cognitive Runtime."""

from __future__ import annotations

import os

import pytest

from lyrion.cognition.composition import build_model_backed_cognitive_runtime
from lyrion.cognition.contracts import CognitiveRequestStatus, ReasonRequest
from lyrion.models.providers.google_gemini_registry import create_gemini_registry


@pytest.mark.asyncio
async def test_live_gemini_cognitive_runtime() -> None:
    """Exercise the complete live Lyrion-to-Gemini cognitive path."""
    if os.getenv("LYRION_LIVE_GEMINI") != "1":
        pytest.skip("set LYRION_LIVE_GEMINI=1 to enable live Gemini validation")

    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY is required for live Gemini validation")

    registry = create_gemini_registry()
    runtime = build_model_backed_cognitive_runtime(registry=registry)

    request = ReasonRequest(
        request_id="reason:gemini:live:test:001",
        objective="Explain in one sentence why provider-neutral model access is useful in Lyrion.",
        context_refs=("context:live-gemini-test",),
        evidence_refs=(),
        created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )

    result = await runtime.reason(request)

    assert result.status is CognitiveRequestStatus.COMPLETED
    assert result.provider == "google"
    assert result.model == "gemini-3.7-flash"
    assert result.answer
    assert result.verification_required is True
