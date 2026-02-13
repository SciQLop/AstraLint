import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .rule import Rule, get_rules_for_suite
from .validation_result import ValidationResultGroup, Severity
from .loader import load_rules_from_dir, load_suite_from_dir
from .file import File
from ..logger import get_logger

__HERE__ = os.path.dirname(__file__)
__SUITES_DIR__ = os.path.abspath(os.path.join(__HERE__, '../suites'))

log = get_logger(__name__)


class ConformanceSuite(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    description: str
    url: str
    rules: list[Rule]

    def merge(self, suite: "ConformanceSuite") -> "ConformanceSuite":
        return ConformanceSuite(
            name=f"{self.name} + {suite.name}",
            description=f"""{self.description}

url: {self.url}

Merged with:

{suite.description}

url: {suite.url}
""",
            url="",
            rules=self.rules + suite.rules
        )

    def validate(self, file: File) -> ValidationResultGroup:
        results = []
        for rule in self.rules:
            log.info(f"Validating rule {rule.name}")
            results.append(rule.check(file))
        return ValidationResultGroup(
            name=self.name,
            rule_reference="",
            results=results,
            severity=Severity.INFO,
        )


class ConformanceSuiteYaml(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    url: str
    rules_lookup_dir: str
    inherit_from: list[str] = Field(default_factory=list,
                                    description="List of suite names to inherit rules from. Not implemented yet.")


def load_suite_from_yaml(path: str) -> ConformanceSuiteYaml:
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    return ConformanceSuiteYaml(**data)


class _ConformanceSuiteProtocolCtor:
    def __init__(self, name: str, rules_lookup_dir: str, **kwargs):
        self.kwargs = kwargs
        self.name = name
        self.rules_lookup_dir = rules_lookup_dir

    def __call__(self) -> ConformanceSuite:
        load_rules_from_dir(self.rules_lookup_dir)
        return ConformanceSuite(**self.kwargs, name=self.name, rules=get_rules_for_suite(self.name))


SUITES = {}


def register_suite(description: str, url: str, name: str, rules_lookup_dir: str, alternative_names: list[str] = None,
                   inherit_from: list[str] = None) -> _ConformanceSuiteProtocolCtor:
    if inherit_from:
        raise NotImplementedError("Inherit from other suites is not implemented yet")
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
