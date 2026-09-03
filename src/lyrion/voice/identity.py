"""Voice Identity orchestration service."""

from __future__ import annotations

from lyrion.voice.contracts import (
    VoiceIdentityMatch,
    VoiceIdentityProvider,
    VoiceIdentityRequest,
)


class VoiceIdentityService:
    """Orchestrate provider-neutral speaker identity resolution."""

    def __init__(self, provider: VoiceIdentityProvider) -> None:
        self._provider = provider

    @property
    def provider(self) -> VoiceIdentityProvider:
        """Return the configured identity provider."""
        return self._provider

    async def identify(
        self,
        request: VoiceIdentityRequest,
    ) -> VoiceIdentityMatch:
        """Resolve speaker identity through the configured provider."""
        result = await self._provider.identify(request)
        if result.request_id != request.request_id:
            raise ValueError("identity provider returned a mismatched request_id")
        return result
