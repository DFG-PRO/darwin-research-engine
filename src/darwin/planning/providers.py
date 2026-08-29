"""Provider-agnostic planning interfaces and adapters."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import uuid4

import httpx

from darwin.config import Settings
from darwin.db.models import ResearchPlanPriority, SourceType, utc_now
from darwin.planning.errors import (
    PlanningConfigurationError,
    PlanningProviderError,
    PlanningProviderTimeout,
)
from darwin.planning.schemas import (
    PlanningProviderResult,
    ProviderPlanProposal,
    ResearchPlanItemProposal,
    ResearchPlanningLimits,
    ResearchPlanningRequest,
)


class PlanningProvider(Protocol):
    """Provider-agnostic boundary for planning proposal generation."""

    identifier: str

    def generate_plan(
        self,
        request: ResearchPlanningRequest,
        limits: ResearchPlanningLimits,
    ) -> PlanningProviderResult:
        """Generate a structured planning proposal without executing research."""


class FakePlanningProvider:
    """Deterministic planning provider for tests and local smoke checks."""

    identifier = "fake"

    def __init__(self, *, mode: str = "success", model: str = "fake-deterministic-planner-v1") -> None:
        self.mode = mode
        self.model = model

    def generate_plan(
        self,
        request: ResearchPlanningRequest,
        limits: ResearchPlanningLimits,
    ) -> PlanningProviderResult:
        if self.mode == "timeout":
            raise PlanningProviderTimeout("fake planning provider timed out")
        if self.mode == "error":
            raise PlanningProviderError("fake planning provider failure")
        if self.mode == "invalid":
            return PlanningProviderResult(
                provider_id=self.identifier,
                provider_model=self.model,
                provider_response_id=f"fake-{uuid4().hex}",
                proposal={"normalized_research_question": request.research_question},
                warnings=["fake invalid structured response"],
            )

        normalized = _normalize_question(request.research_question)
        categories = ["background", "primary-evidence"]
        desired_sources = request.desired_source_types or [SourceType.WEB_PAGE, SourceType.DOCUMENT]
        source_requirement = desired_sources[0]
        freshness_note = ""
        if request.freshness_start or request.freshness_end:
            freshness_note = " within the requested freshness window"
        domain_note = ""
        if request.domain_constraints:
            domain_note = f" constrained to {', '.join(request.domain_constraints)}"

        proposal = ProviderPlanProposal(
            normalized_research_question=normalized,
            proposed_objective=request.objective
            or f"Develop an evidence-backed answer to: {request.research_question}",
            proposed_scope=request.scope or "Plan bounded source discovery and evidence review only.",
            proposed_exclusions=request.exclusions,
            proposed_assumptions=request.assumptions,
            proposed_research_categories=categories,
            expected_evidence_types=["primary documentation", "corroborating analysis"],
            suggested_source_types=desired_sources,
            tasks=[
                ResearchPlanItemProposal(
                    item_key="background-map",
                    requirement=f"Map the key entities, definitions, and decision context for {normalized}.",
                    category="background",
                    priority=ResearchPlanPriority.MEDIUM,
                    required=False,
                    expected_source_type=source_requirement,
                    expected_evidence_types=["contextual source"],
                    suggested_source_types=desired_sources,
                    completion_criteria=["Key terms and scope boundaries are explicit."],
                ),
                ResearchPlanItemProposal(
                    item_key="primary-evidence",
                    requirement=(
                        "Collect primary or authoritative evidence relevant to the research question"
                        f"{freshness_note}{domain_note}."
                    ),
                    category="primary-evidence",
                    priority=ResearchPlanPriority.HIGH,
                    required=True,
                    expected_source_type=source_requirement,
                    expected_evidence_types=["primary documentation"],
                    suggested_source_types=desired_sources,
                    completion_criteria=[
                        "At least one authoritative source candidate is identified for later acquisition."
                    ],
                ),
            ][: limits.max_plan_items],
            planner_warnings=[
                "Fake provider output is deterministic and not evidence.",
                "Planner proposal does not execute acquisition.",
            ],
            method_version="research-planning-1.9a",
            prompt_version=None,
            schema_version="research-plan-proposal-schema-1.9a",
            planning_provenance={"provider": "fake", "deterministic": True},
        )
        return PlanningProviderResult(
            provider_id=self.identifier,
            provider_model=self.model,
            provider_response_id=f"fake-{uuid4().hex}",
            proposal=proposal,
            warnings=[],
            provider_metadata={"deterministic": True},
            usage_metadata={"request_count": 1},
            created_at=utc_now(),
        )


class OpenAIPlanningProvider:
    """Minimal OpenAI Responses API adapter for structured planning proposals."""

    identifier = "openai"
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, settings: Settings) -> None:
        if settings.openai_api_key is None:
            raise PlanningConfigurationError("DARWIN_OPENAI_API_KEY is required")
        self.api_key = settings.openai_api_key.get_secret_value()
        self.model = settings.research_planning_model
        self.timeout_seconds = settings.research_planning_timeout_seconds
        self.method_version = settings.research_planning_method_version
        self.prompt_version = settings.research_planning_prompt_version
        self.schema_version = settings.research_planning_schema_version

    def generate_plan(
        self,
        request: ResearchPlanningRequest,
        limits: ResearchPlanningLimits,
    ) -> PlanningProviderResult:
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": self._system_prompt(limits),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": request.model_dump_json(),
                        }
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "research_plan_proposal",
                    "strict": True,
                    "schema": _proposal_json_schema(),
                }
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            response_payload = response.json()
        except httpx.TimeoutException as exc:
            raise PlanningProviderTimeout("planning provider request timed out") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise PlanningProviderError("planning provider request failed") from exc

        output = _extract_response_json(response_payload)
        return PlanningProviderResult(
            provider_id=self.identifier,
            provider_model=self.model,
            provider_response_id=response_payload.get("id"),
            proposal=output,
            provider_metadata={"endpoint": "responses"},
            usage_metadata=response_payload.get("usage") or {},
            created_at=utc_now(),
        )

    def _system_prompt(self, limits: ResearchPlanningLimits) -> str:
        return (
            "Generate only a bounded research plan proposal. The output is not evidence, "
            "not a claim, not a conclusion, and must not assert that facts are true. "
            f"Use method_version={self.method_version}, prompt_version={self.prompt_version}, "
            f"schema_version={self.schema_version}. "
            f"Limits: max_plan_items={limits.max_plan_items}, "
            f"max_required_plan_items={limits.max_required_plan_items}, "
            f"max_categories={limits.max_categories}."
        )


def build_planning_provider(settings: Settings) -> PlanningProvider:
    """Build the configured planning provider without exposing credentials."""

    if settings.research_planning_provider == "openai":
        return OpenAIPlanningProvider(settings)
    return FakePlanningProvider(model=settings.research_planning_model)


def _normalize_question(question: str) -> str:
    stripped = " ".join(question.strip().split())
    return stripped if stripped.endswith("?") else f"{stripped}?"


def _extract_response_json(payload: dict[str, Any]) -> dict[str, Any]:
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if isinstance(content, dict) and "json" in content:
                return content["json"]
            if isinstance(content, dict) and "text" in content:
                try:
                    return ProviderPlanProposal.model_validate_json(content["text"]).model_dump(mode="json")
                except ValueError:
                    continue
    raise PlanningProviderError("planning provider returned no structured JSON")


def _proposal_json_schema() -> dict[str, Any]:
    return ProviderPlanProposal.model_json_schema()
