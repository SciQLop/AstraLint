from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from ..file import File
from ..rule import RULES, Rule
from ..validation_result import ValidationResult, ValidationResultGroup
from .assertions.base import BaseEvaluable, get_assertion_union


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
        return ValidationResult(
            valid=valid,
            reference=self.reference,
            severity=self.severity,
            message=message,
            target=target,
        )

    def check(self, file: File) -> ValidationResult | ValidationResultGroup:
        results = []
        for assertion in self.assertions:
            assert isinstance(assertion, BaseEvaluable)
            results.append(assertion.evaluate(file, severity=self.severity))
        return ValidationResultGroup(
            name=self.name,
            rule_reference=self.reference,
            results=results,
            severity=self.severity,
            url=self.url,
        )


def load_yaml_rule(yaml_path: Path) -> YamlRule:
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    return YamlRule(**data)


def register_yaml_rule(yaml_path: Path):
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    suite = data["suite"]
    rule = YamlRule(**data)
    # Idempotent: a suite may be (re)loaded several times — directly and as a
    # parent of an inheriting suite — so replace any rule of the same name
    # instead of appending a duplicate.
    rules = RULES.setdefault(suite, [])
    for index, existing in enumerate(rules):
        if existing.name == rule.name:
            rules[index] = rule
            return
    rules.append(rule)
