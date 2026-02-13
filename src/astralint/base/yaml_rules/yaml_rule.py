from pydantic import BaseModel, ConfigDict, model_validator
from pathlib import Path
from typing import Any
import yaml

from ..file import File
from ..validation_result import ValidationResult, ValidationResultGroup, Severity
from ..rule import RULES, Rule
from .assertions.registry import get_assertion_union
from .assertions.base import BaseAssertion


class YamlRuleAssertion(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: str
    check: str
    message: str


class YamlRule(Rule):
    assertions: list[Any]

    @model_validator(mode="before")
    @classmethod
    def parse_assertions(cls, data: dict) -> dict:
        """Parse assertions using the discriminated union."""
        assertion = get_assertion_union()
        from pydantic import TypeAdapter
        adapter = TypeAdapter(list[assertion])
        data["assertions"] = adapter.validate_python(data.get("assertions", []))
        return data

    def _format_result(self, valid: bool, message: str, target: str = "Global") -> ValidationResult:
        return ValidationResult(valid=valid, reference=self.reference, severity=self.severity, message=message,
                                target=target)

    def check(self, file: File) -> ValidationResult | ValidationResultGroup:
        results = []
        for assertion in self.assertions:
            assert isinstance(assertion, BaseAssertion)
            results.append(assertion.evaluate(file))
        return ValidationResultGroup(
            name=self.name,
            rule_reference=self.reference,
            results=results,
            severity=self.severity,
        )


def load_yaml_rule(yaml_path: Path) -> YamlRule:
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    return YamlRule(**data)


def register_yaml_rule(yaml_path: Path):
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    suite = data["suite"]
    rule = load_yaml_rule(yaml_path)
    if suite not in RULES:
        RULES[suite] = []
    RULES[suite].append(rule)
