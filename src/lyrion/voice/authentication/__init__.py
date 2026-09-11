"""Provider-neutral voice authentication boundary."""

from lyrion.voice.authentication.contracts import (
    VoiceAuthenticationAssurance,
    VoiceAuthenticationEvidence,
    VoiceAuthenticationMethod,
    VoiceAuthenticationRequest,
    VoiceAuthenticationResult,
    VoiceAuthenticationStatus,
)
from lyrion.voice.authentication.service import VoiceAuthenticationService
from lyrion.voice.authentication.verifier import (
    DeterministicVoiceAuthenticationVerifier,
    VoiceAuthenticationVerifier,
    VoiceVerificationObservation,
)

__all__ = [
    "VoiceAuthenticationAssurance",
    "VoiceAuthenticationEvidence",
    "VoiceAuthenticationMethod",
    "VoiceAuthenticationRequest",
    "VoiceAuthenticationResult",
    "VoiceAuthenticationStatus",
    "VoiceAuthenticationService",
    "DeterministicVoiceAuthenticationVerifier",
    "VoiceAuthenticationVerifier",
    "VoiceVerificationObservation",
]
