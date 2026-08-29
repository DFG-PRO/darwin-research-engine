"""Service layer for auditable external source acquisition."""

from __future__ import annotations

from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from darwin.acquisition.errors import AcquisitionProviderError, AcquisitionProviderTimeout
from darwin.acquisition.normalization import normalize_candidate, sanitize_metadata
from darwin.acquisition.providers import ResearchProvider
from darwin.acquisition.schemas import (
    AcquisitionRequest,
    AcquisitionResult,
    ProviderSearchResult,
    SourceCandidateResult,
)
from darwin.db.models import (
    AcquisitionStatus,
    ResearchAcquisitionRequest,
    Source,
    SourceCandidate,
    SourceCandidateRegistrationStatus,
    SourceType,
    utc_now,
)
from darwin.research import ResearchService


class AcquisitionService:
    """Coordinate provider discovery, audit history, deduplication, and source registration."""

    def __init__(self, session: Session, provider: ResearchProvider) -> None:
        self.session = session
        self.provider = provider
        self.research_service = ResearchService(session)

    def acquire(self, request: AcquisitionRequest) -> AcquisitionResult:
        self.research_service.get_research_run(request.research_run_id)

        provider_result = self._safe_provider_search(request)
        record = self._persist_request(request, provider_result)
        candidates = self._persist_candidates(record, provider_result)

        record.candidate_count = len(candidates)
        record.registered_source_count = len(
            [
                candidate
                for candidate in candidates
                if candidate.registered_source_id is not None
                and candidate.registration_status
                in {
                    SourceCandidateRegistrationStatus.REGISTERED_NEW_SOURCE,
                    SourceCandidateRegistrationStatus.REGISTERED_EXISTING_SOURCE,
                }
            ]
        )
        self.session.flush()
        return self._build_result(record, candidates)

    def _safe_provider_search(
        self,
        request: AcquisitionRequest,
    ) -> ProviderSearchResult:
        try:
            return self.provider.search(request)
        except AcquisitionProviderTimeout as exc:
            return ProviderSearchResult(
                provider_id=self.provider.identifier,
                original_query=request.query,
                status=AcquisitionStatus.FAILED,
                errors=[str(exc) or "provider request timed out"],
            )
        except AcquisitionProviderError as exc:
            return ProviderSearchResult(
                provider_id=self.provider.identifier,
                original_query=request.query,
                status=AcquisitionStatus.FAILED,
                errors=[str(exc) or "provider request failed"],
            )
        except Exception as exc:
            return ProviderSearchResult(
                provider_id=self.provider.identifier,
                original_query=request.query,
                status=AcquisitionStatus.FAILED,
                errors=[f"unexpected provider failure: {exc.__class__.__name__}"],
            )

    def _persist_request(
        self,
        request: AcquisitionRequest,
        provider_result: ProviderSearchResult,
    ) -> ResearchAcquisitionRequest:
        record = ResearchAcquisitionRequest(
            research_run_id=request.research_run_id,
            provider_id=provider_result.provider_id,
            provider_request_id=provider_result.provider_request_id,
            query=request.query,
            category=request.category,
            requested_source_types=[source_type.value for source_type in request.requested_source_types],
            freshness_start=request.freshness_start,
            freshness_end=request.freshness_end,
            domain_constraints=request.domain_constraints,
            result_limit=request.result_limit,
            status=provider_result.status,
            executed_at=provider_result.executed_at,
            completed_at=utc_now(),
            warning_count=len(provider_result.warnings),
            error_count=len(provider_result.errors),
            retry_attempts=provider_result.retry_attempts,
            request_count=provider_result.request_count,
            usage_units=_decimal_or_none(provider_result.usage_units),
            estimated_cost=_decimal_or_none(provider_result.estimated_cost),
            actual_cost=_decimal_or_none(provider_result.actual_cost),
            warnings=provider_result.warnings,
            errors=provider_result.errors,
            request_metadata=sanitize_metadata(request.metadata),
            provider_metadata=sanitize_metadata(provider_result.provider_metadata),
            rate_limit_metadata=sanitize_metadata(provider_result.rate_limit_metadata),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def _persist_candidates(
        self,
        record: ResearchAcquisitionRequest,
        provider_result: ProviderSearchResult,
    ) -> list[SourceCandidate]:
        candidates: list[SourceCandidate] = []
        seen_deduplication_keys: dict[str, SourceCandidate] = {}

        for provider_candidate in provider_result.candidates:
            normalized = normalize_candidate(provider_candidate)
            candidate = SourceCandidate(
                acquisition_request=record,
                provider_candidate_id=provider_candidate.provider_candidate_id,
                canonical_locator=normalized.canonical_locator,
                normalized_locator=normalized.normalized_locator,
                deduplication_key=normalized.deduplication_key,
                title=provider_candidate.title,
                publisher=normalized.publisher,
                normalized_domain=normalized.normalized_domain,
                publication_date=provider_candidate.publication_date,
                retrieved_at=normalized.retrieved_at,
                snippet=provider_candidate.snippet,
                provider_rank=provider_candidate.provider_rank,
                source_type=normalized.source_type,
                provider_metadata=normalized.provider_metadata,
            )
            self.session.add(candidate)
            self.session.flush()

            duplicate = seen_deduplication_keys.get(candidate.deduplication_key)
            if duplicate is not None:
                candidate.registration_status = (
                    SourceCandidateRegistrationStatus.DUPLICATE_CANDIDATE
                )
                candidate.duplicate_of_candidate = duplicate
                candidates.append(candidate)
                continue

            seen_deduplication_keys[candidate.deduplication_key] = candidate
            self._register_candidate_source(candidate, record.provider_id)
            candidates.append(candidate)

        self.session.flush()
        return candidates

    def _register_candidate_source(
        self,
        candidate: SourceCandidate,
        provider_id: str,
    ) -> None:
        if candidate.source_type is None:
            candidate.registration_status = SourceCandidateRegistrationStatus.NOT_REGISTERED
            return

        existing_source = self._find_existing_source(
            source_type=candidate.source_type,
            canonical_locator=candidate.normalized_locator,
        )
        source = self.research_service.register_source(
            source_type=candidate.source_type,
            canonical_locator=candidate.normalized_locator,
            title=candidate.title,
            publisher=candidate.publisher,
            publication_date=candidate.publication_date,
            metadata={
                "acquisition": {
                    "provider_id": provider_id,
                    "source_candidate_id": str(candidate.id),
                    "provider_candidate_id": candidate.provider_candidate_id,
                    "provider_rank": candidate.provider_rank,
                }
            },
        )
        candidate.registered_source = source
        candidate.registration_status = (
            SourceCandidateRegistrationStatus.REGISTERED_EXISTING_SOURCE
            if existing_source is not None
            else SourceCandidateRegistrationStatus.REGISTERED_NEW_SOURCE
        )

    def _find_existing_source(self, *, source_type: SourceType, canonical_locator: str) -> Source | None:
        return self.session.execute(
            select(Source).where(
                Source.source_type == source_type,
                Source.canonical_locator == canonical_locator,
            )
        ).scalar_one_or_none()

    def _build_result(
        self,
        record: ResearchAcquisitionRequest,
        candidates: list[SourceCandidate],
    ) -> AcquisitionResult:
        return AcquisitionResult(
            acquisition_id=record.id,
            research_run_id=record.research_run_id,
            provider_id=record.provider_id,
            provider_request_id=record.provider_request_id,
            query=record.query,
            status=record.status,
            executed_at=record.executed_at,
            completed_at=record.completed_at,
            candidate_count=record.candidate_count,
            registered_source_count=record.registered_source_count,
            warnings=record.warnings,
            errors=record.errors,
            retry_attempts=record.retry_attempts,
            request_count=record.request_count,
            candidates=[
                SourceCandidateResult(
                    candidate_id=candidate.id,
                    provider_candidate_id=candidate.provider_candidate_id,
                    canonical_locator=candidate.canonical_locator,
                    normalized_locator=candidate.normalized_locator,
                    title=candidate.title,
                    publisher=candidate.publisher,
                    normalized_domain=candidate.normalized_domain,
                    publication_date=candidate.publication_date,
                    retrieved_at=candidate.retrieved_at,
                    provider_rank=candidate.provider_rank,
                    source_type=candidate.source_type,
                    registration_status=candidate.registration_status,
                    duplicate_of_candidate_id=candidate.duplicate_of_candidate_id,
                    registered_source_id=candidate.registered_source_id,
                )
                for candidate in candidates
            ],
        )


def _decimal_or_none(value: Decimal | float | int | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
