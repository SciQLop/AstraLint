from typing import Literal

from pydantic import BaseModel

from ..base.conformance_suite import ConformanceSuite
from ..base.file import File
from ..base.validation_result import Severity, ValidationResultGroup
from ..codecs.cdf import CdfCodec
from .apply import apply_fixes
from .engine import resolve
from .models import Fix


class ConvergenceReport(BaseModel):
    iterations: int
    applied: list[Fix]
    staged: list[Fix]
    remaining_errors: int
    converged: bool
    stopped_reason: Literal["converged", "no_progress", "max_iter"]


def _failure_signature(results: ValidationResultGroup) -> frozenset[tuple[str, str]]:
    sig: set[tuple[str, str]] = set()

    def walk(group: ValidationResultGroup) -> None:
        for r in group.results:
            if isinstance(r, ValidationResultGroup):
                walk(r)
            elif not r.valid and r.severity != Severity.SKIPPED:
                sig.add((r.reference, r.target))

    walk(results)
    return frozenset(sig)


def _load(cdf_bytes: bytes) -> File:
    result = CdfCodec.load(cdf_bytes)
    if result is None:
        raise ValueError("Failed to parse CDF bytes")
    return result


def converge(
    cdf_bytes: bytes, suite: ConformanceSuite, max_iter: int = 10
) -> tuple[ConvergenceReport, bytes]:
    applied: list[Fix] = []
    staged: list[Fix] = []
    iterations = 0
    stopped: Literal["converged", "no_progress", "max_iter"] = "max_iter"
    prev_signature: frozenset[tuple[str, str]] | None = None

    while iterations < max_iter:
        file = _load(cdf_bytes)
        results = suite.run(file)
        if not results.has_errors():
            stopped = "converged"
            break

        signature = _failure_signature(results)
        if signature == prev_signature:
            stopped = "no_progress"
            break
        prev_signature = signature

        fixes = resolve(file, results.failures_only())
        auto = [f for f in fixes if f.auto]
        staged = [f for f in fixes if not f.auto]
        if not auto:
            stopped = "no_progress"
            break

        cdf_bytes = apply_fixes(cdf_bytes, auto)
        applied.extend(auto)
        iterations += 1

    final = suite.run(_load(cdf_bytes))
    report = ConvergenceReport(
        iterations=iterations,
        applied=applied,
        staged=staged,
        remaining_errors=final.count_by_severity()["ERROR"],
        converged=not final.has_errors(),
        stopped_reason=stopped,
    )
    return report, cdf_bytes
