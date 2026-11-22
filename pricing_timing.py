"""Opt-in, request-scoped timing records for pricing benchmarks."""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter_ns
from typing import Iterator
from uuid import uuid4


@dataclass(frozen=True)
class StageTiming:
    stage: str
    duration_ns: int
    status: str
    error_type: str = ""
    attempt_number: int | None = None


@dataclass
class PricingMeasurement:
    scenario: str
    mode: str
    input_dataset_id: str
    model: str = ""
    run_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    stage_timings: list[StageTiming] = field(default_factory=list)
    attempt_count: int = 0
    retry_attempts: int = 0
    provider_request_count: int = 0
    run_status: str = "running"
    failure_type: str = ""
    provider_status_code: int | None = None

    @contextmanager
    def measure(self, stage: str) -> Iterator[None]:
        started_ns = perf_counter_ns()
        error_type = ""
        try:
            yield
        except BaseException as error:
            error_type = _error_type(error)
            self.failure_type = error_type
            self.run_status = "failure"
            raise
        finally:
            self.stage_timings.append(
                StageTiming(
                    stage=stage,
                    duration_ns=perf_counter_ns() - started_ns,
                    status="failure" if error_type else "success",
                    error_type=error_type,
                )
            )

    @contextmanager
    def measure_attempt(self) -> Iterator[int]:
        attempt_number = self.attempt_count + 1
        started_ns = perf_counter_ns()
        error_type = ""
        try:
            yield attempt_number
        except BaseException as error:
            error_type = _error_type(error)
            self.failure_type = error_type
            self.run_status = "failure"
            raise
        finally:
            self.attempt_count += 1
            self.retry_attempts = max(0, self.attempt_count - 1)
            self.stage_timings.append(
                StageTiming(
                    stage="llm_pricing_attempt",
                    duration_ns=perf_counter_ns() - started_ns,
                    status="failure" if error_type else "success",
                    error_type=error_type,
                    attempt_number=attempt_number,
                )
            )

    def mark_failure(
        self,
        error: BaseException,
        *,
        provider_status_code: int | None = None,
    ) -> None:
        self.run_status = "failure"
        self.failure_type = _error_type(error)
        self.provider_status_code = provider_status_code

    def mark_success(self) -> None:
        self.run_status = "success"


_ACTIVE_MEASUREMENT: ContextVar[PricingMeasurement | None] = ContextVar(
    "active_pricing_measurement",
    default=None,
)
_ACTIVE_REQUEST_BUDGET: ContextVar[ExternalRequestBudget | None] = ContextVar(
    "active_external_request_budget",
    default=None,
)


@dataclass
class ExternalRequestBudget:
    max_requests: int
    request_count: int = 0

    def consume(self) -> None:
        if self.request_count >= self.max_requests:
            raise ExternalRequestBudgetExceeded()
        self.request_count += 1


class ExternalRequestBudgetExceeded(RuntimeError):
    failure_code = "external_request_budget_exceeded"

    def __init__(self) -> None:
        super().__init__(self.failure_code)


@contextmanager
def activate_measurement(
    measurement: PricingMeasurement,
) -> Iterator[PricingMeasurement]:
    token = _ACTIVE_MEASUREMENT.set(measurement)
    try:
        yield measurement
    finally:
        _ACTIVE_MEASUREMENT.reset(token)


@contextmanager
def activate_request_budget(
    budget: ExternalRequestBudget,
) -> Iterator[ExternalRequestBudget]:
    token = _ACTIVE_REQUEST_BUDGET.set(budget)
    try:
        yield budget
    finally:
        _ACTIVE_REQUEST_BUDGET.reset(token)


def record_external_request() -> None:
    budget = _ACTIVE_REQUEST_BUDGET.get()
    if budget is not None:
        budget.consume()

    measurement = _ACTIVE_MEASUREMENT.get()
    if measurement is not None:
        measurement.provider_request_count += 1


def measure_stage(stage: str):
    """Return a timer when a benchmark is active, otherwise a no-op context."""
    measurement = _ACTIVE_MEASUREMENT.get()
    if measurement is None:
        return nullcontext()
    return measurement.measure(stage)


def _error_type(error: BaseException) -> str:
    return str(getattr(error, "failure_code", type(error).__name__))
