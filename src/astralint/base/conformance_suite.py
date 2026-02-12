import os
from dataclasses import dataclass
from typing import Optional

from .rule import Rule, get_rules_for_suite
from .validation_result import ValidationResult
from .loader import load_rules_from_dir, load_suite_from_dir
from .file import File

__HERE__ = os.path.dirname(__file__)
__SUITES_DIR__ = os.path.abspath(os.path.join(__HERE__, '../suites'))


@dataclass
class ConformanceSuite:
    description: str
    url: str
    rules: list[Rule]

    def merge(self, suite: "ConformanceSuite") -> "ConformanceSuite":
        return ConformanceSuite(
            description=f"""{self.description}

url: {self.url}

Merged with:

{suite.description}

url: {suite.url}
""",
            url="",
            rules=self.rules + suite.rules
        )

    def validate(self, file: File) -> list[ValidationResult]:
        results = []
        for rule in self.rules:
            results.extend(rule.check(file))
        return results


class _ConformanceSuiteProtocolCtor:
    def __init__(self, name: str, rules_lookup_dir: str, **kwargs):
        self.kwargs = kwargs
        self.name = name
        self.rules_lookup_dir = rules_lookup_dir

    def __call__(self) -> ConformanceSuite:
        load_rules_from_dir(self.rules_lookup_dir)
        return ConformanceSuite(**self.kwargs, rules=get_rules_for_suite(self.name))


SUITES = {}


def register_suite(description: str, url: str, name: str, rules_lookup_dir: str, alternative_names: list[str] = None):
    ctor = _ConformanceSuiteProtocolCtor(description=description, url=url, name=name, rules_lookup_dir=rules_lookup_dir)
    SUITES[name] = ctor
    if alternative_names:
        for alt_name in alternative_names:
            SUITES[alt_name] = ctor
    return ctor


def get_suite(name: str) -> Optional[ConformanceSuite]:
    if name not in SUITES:
        load_suite_from_dir(__SUITES_DIR__, name)
    if ctor := SUITES.get(name):
        return ctor()
    return None


def list_suites() -> list[str]:
    return list(SUITES.keys())
