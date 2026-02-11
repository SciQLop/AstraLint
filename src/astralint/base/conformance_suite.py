from dataclasses import dataclass
from typing import Protocol

from .rule import Rule
from .validation_result import ValidationResult


@dataclass
class ConformanceSuite:
    description: str
    url: str
    rules: list[Rule]

    def merge(self, suite: "ConformanceSuite"):
        return ConformanceSuite(self.rules + suite.rules)

    def validate(self, file) -> list[ValidationResult]:
        results = []
        for rule in self.rules:
            results.extend(rule.check(file))
        return results


class _ConformanceSuiteProtocolCtor:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self) -> ConformanceSuite:
        return ConformanceSuite(**self.kwargs)


def build_suite(**kwargs) -> _ConformanceSuiteProtocolCtor:
    return _ConformanceSuiteProtocolCtor(**kwargs)
