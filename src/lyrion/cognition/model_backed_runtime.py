"""Model-backed Cognitive Runtime implementation for Lyrion."""

from __future__ import annotations

from datetime import UTC, datetime

from lyrion.cognition.contracts import (
    CognitiveRequestStatus,
    CognitiveResult,
    ReasonRequest,
)
from lyrion.models.contracts import (
    ModelBudget,
    ModelCapability,
    ModelModality,
    ModelRequest,
)
from lyrion.models.gateway import ModelGateway


class ModelBackedCognitiveRuntime:
    """Translate bounded cognitive requests into model-gateway calls."""

    def __init__(
        self,
        *,
        gateway: ModelGateway,
    ) -> None:
        """Initialize the runtime with a provider-neutral Model Gateway."""
        self._gateway = gateway

    @property
    def gateway(self) -> ModelGateway:
        """Return the configured Model Gateway."""
        return self._gateway

    async def reason(
        self,
        request: ReasonRequest,
    ) -> CognitiveResult:
        """Process one bounded reasoning request through the Model Fabric."""
        if request.budget.max_model_calls < 1:
            return self._failed_result(
                request,
                status=CognitiveRequestStatus.REJECTED,
            )

        try:
            model_request = ModelRequest(
                request_id=request.request_id,
                objective=request.objective,
                context_refs=request.context_refs,
                evidence_refs=request.evidence_refs,
                required_capabilities=self._normalize_capabilities(
                    request.required_capabilities,
                ),
                modality=ModelModality.TEXT,
                reasoning_difficulty=self._reasoning_difficulty(request),
                risk_level=request.risk_class,
                privacy_required=False,
                network_required=False,
                budget=ModelBudget(
                    max_runtime_seconds=request.budget.max_runtime_seconds,
                    max_cost_units=request.budget.max_cost_units,
                    max_output_tokens=4096,
                ),
                preferred_targets=(),
                created_at=request.created_at,
            )

            response = await self._gateway.generate(model_request)
        except TimeoutError:
            return self._failed_result(request, status=CognitiveRequestStatus.TIMEOUT)
        except (ValueError, TypeError):
            return self._failed_result(request, status=CognitiveRequestStatus.REJECTED)
        except Exception:
            return self._failed_result(request, status=CognitiveRequestStatus.FAILED)

        verification_required = (
            request.constraints.require_verification
            or bool(request.verification_requirements)
        )

        return CognitiveResult(
            request_id=request.request_id,
            status=CognitiveRequestStatus.COMPLETED,
            answer=response.content,
            proposed_plan=(),
            uncertainty=1.0 - response.confidence,
            confidence=response.confidence,
            evidence_refs=request.evidence_refs,
            provider=response.provider,
            model=response.model,
            verification_required=verification_required,
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def _normalize_capabilities(
        capabilities: tuple[str, ...],
    ) -> tuple[ModelCapability, ...]:
        """Convert cognitive capability names into model capabilities."""
        normalized: list[ModelCapability] = []

        for capability in capabilities:
            try:
                model_capability = ModelCapability(capability)
            except ValueError as exc:
                raise ValueError(
                    f"unsupported model capability: {capability}"
                ) from exc
            if model_capability not in normalized:
                normalized.append(model_capability)

        if not normalized:
            normalized.append(ModelCapability.GENERATION)

        return tuple(normalized)

    @staticmethod
    def _reasoning_difficulty(
        request: ReasonRequest,
    ) -> float:
        """Derive a bounded routing difficulty from request complexity."""
        return min(
            1.0,
            0.5 + (0.1 * len(request.required_capabilities)),
        )

    @staticmethod
    def _failed_result(
        request: ReasonRequest,
        *,
        status: CognitiveRequestStatus,
    ) -> CognitiveResult:
        """Build a fail-closed cognitive result."""
        return CognitiveResult(
            request_id=request.request_id,
            status=status,
            answer=None,
            proposed_plan=(),
            uncertainty=1.0,
            confidence=0.0,
            evidence_refs=(),
            provider=None,
            model=None,
            verification_required=True,
            created_at=datetime.now(UTC),
        )


def build_model_backed_cognitive_runtime(
    *,
    gateway: ModelGateway,
) -> ModelBackedCognitiveRuntime:
    """Build the model-backed Cognitive Runtime."""
    return ModelBackedCognitiveRuntime(gateway=gateway)
