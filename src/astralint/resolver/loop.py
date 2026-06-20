from typing import Literal

from pydantic import BaseModel

from ..base.conformance_suite import ConformanceSuite
from ..base.file import File
from ..base.validation_result import ValidationResultGroup
from ..codecs.cdf import CdfCodec
from .apply import apply_fixes
from .engine import _iter_failures, resolve
from .models import Fix


class ConvergenceReport(BaseModel):
    iterations: int
    applied: list[Fix]
    staged: list[Fix]
    remaining_errors: int
    converged: bool
    stopped_reason: Literal["converged", "no_progress", "max_iter"]


def _failure_signature(results: ValidationResultGroup) -> frozenset[tuple[str, str]]:
    # Key on the enclosing rule reference (carried by _iter_failures), not the
    # leaf's own reference which is empty — otherwise distinct rules failing on
    # the same target collapse to one signature and trigger a false no-progress.
    return frozenset((reference, leaf.target) for reference, leaf in _iter_failures(results))


def _load(cdf_bytes: bytes, filename: str | None = None) -> File:
    result = CdfCodec.load(cdf_bytes)
    if result is None:
        raise ValueError("Failed to parse CDF bytes")
    # The byte round-trip drops the original filename (the codec uses a
    # placeholder); restore it so filename-derived resolvers can run.
    if filename is not None:
        result.filename = filename
    return result


def converge(
    cdf_bytes: bytes,
    suite: ConformanceSuite,
    max_iter: int = 10,
    filename: str | None = None,
) -> tuple[ConvergenceReport, bytes]:
    applied: list[Fix] = []
    iterations = 0
    stopped: Literal["converged", "no_progress", "max_iter"] = "max_iter"
    prev_signature: frozenset[tuple[str, str]] | None = None

    while iterations < max_iter:
        file = _load(cdf_bytes, filename)
        results = suite.run(file)
        if not results.has_errors():
            stopped = "converged"
            break

        signature = _failure_signature(results)
        if signature == prev_signature:
            stopped = "no_progress"
            break
        prev_signature = signature

        auto = [f for f in resolve(file, results.failures_only()) if f.auto]
        if not auto:
            stopped = "no_progress"
            break

        cdf_bytes = apply_fixes(cdf_bytes, auto)
        applied.extend(auto)
        iterations += 1

    # Recompute staged suggestions against the FINAL file state so they reflect
    # what still needs review after all auto-fixes (not a stale pre-mutation set).
    final_file = _load(cdf_bytes, filename)
    final = suite.run(final_file)
    staged = [f for f in resolve(final_file, final.failures_only()) if not f.auto]
    report = ConvergenceReport(
        iterations=iterations,
        applied=applied,
        staged=staged,
        remaining_errors=final.count_by_severity()["ERROR"],
        converged=not final.has_errors(),
        stopped_reason=stopped,
    )
    return report, cdf_bytes
