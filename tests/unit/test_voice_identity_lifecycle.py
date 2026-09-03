from lyrion.voice.contracts import VoiceIdentityProfileStatus
from lyrion.voice.lifecycle import VoiceIdentityProfileTransitionPolicy


def test_transition_policy_allows_explicit_transition() -> None:
    policy = VoiceIdentityProfileTransitionPolicy(
        {
            VoiceIdentityProfileStatus.PENDING: frozenset({
                VoiceIdentityProfileStatus.ACTIVE,
            }),
        }
    )

    assert policy.is_allowed(
        VoiceIdentityProfileStatus.PENDING,
        VoiceIdentityProfileStatus.ACTIVE,
    )


def test_transition_policy_rejects_unconfigured_transition() -> None:
    policy = VoiceIdentityProfileTransitionPolicy(
        {
            VoiceIdentityProfileStatus.PENDING: frozenset({
                VoiceIdentityProfileStatus.ACTIVE,
            }),
        }
    )

    assert not policy.is_allowed(
        VoiceIdentityProfileStatus.ACTIVE,
        VoiceIdentityProfileStatus.PENDING,
    )


def test_transition_policy_validate_rejects_transition() -> None:
    policy = VoiceIdentityProfileTransitionPolicy(
        {
            VoiceIdentityProfileStatus.PENDING: frozenset({
                VoiceIdentityProfileStatus.ACTIVE,
            }),
        }
    )

    try:
        policy.validate(
            VoiceIdentityProfileStatus.ACTIVE,
            VoiceIdentityProfileStatus.PENDING,
        )
    except ValueError as exc:
        assert "not allowed" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_transition_policy_is_explicitly_configured() -> None:
    policy = VoiceIdentityProfileTransitionPolicy({})

    assert not policy.is_allowed(
        VoiceIdentityProfileStatus.REVOKED,
        VoiceIdentityProfileStatus.ACTIVE,
    )
