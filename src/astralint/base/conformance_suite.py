import re
from collections.abc import Iterable, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ..logger import get_logger
from .file import File
from .loader import load_rules_from_dir, load_suite_from_dir
from .rule import Rule, get_rules_for_suite
from .validation_result import Severity, ValidationResultGroup

_SUITES_DIR = (Path(__file__).parent / ".." / "suites").resolve()

log = get_logger(__name__)


def _matches_any_pattern(rule: Rule, patterns: list[str]) -> bool:
    for pattern in patterns:
        if re.fullmatch(pattern, rule.name) or re.fullmatch(pattern, rule.reference):
            return True
    return False


def filter_rules(
    rules: list[Rule], select: list[str] | None, ignore: list[str] | None
) -> list[Rule]:
    assert not (select and ignore), "Cannot use both select and ignore at the same time"
    if select:
        rules = [rule for rule in rules if _matches_any_pattern(rule, select)]
    if ignore:
        rules = [rule for rule in rules if not _matches_any_pattern(rule, ignore)]
    return rules


def load_extra_rules(directories: Iterable[Path]) -> None:
    """Load YAML rules from additional directories (cfg.extra_rules).

    Each YAML rule self-declares its target suite via the ``suite`` field,
    so loaded rules join the appropriate suite the next time it is constructed.
    """
    for directory in directories:
        path = Path(directory)
        if not path.is_dir():
            raise FileNotFoundError(f"extra_rules path is not a directory: {path}")
        load_rules_from_dir(str(path))


def apply_severity_overrides(
    rules: Sequence[Rule], overrides: dict[str, Severity]
) -> Sequence[Rule]:
    if not overrides:
        return rules
    return [
        rule.model_copy(update={"severity": overrides[rule.reference]})
        if rule.reference in overrides
        else rule
        for rule in rules
    ]


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
            rules=self.rules + suite.rules,
        )

    def run(
        self,
        file: File,
        select: list[str] | None = None,
        ignore: list[str] | None = None,
        severity_overrides: dict[str, Severity] | None = None,
    ) -> ValidationResultGroup:
        from .yaml_rules.assertions.base import clear_flatten_cache

        results = []
        rules = filter_rules(self.rules, select, ignore)
        rules = apply_severity_overrides(rules, severity_overrides or {})
        clear_flatten_cache()
        for rule in rules:
            log.debug(f"Validating rule {rule.name}")
            results.append(rule.check(file))
        return ValidationResultGroup(
            name=f"AstraLint Results for suite '{self.name}' on file '{file.filename}'",
            rule_reference="",
            results=results,
            severity=Severity.INFO,
            message=f"Validation completed for suite '{self.name}' with {len(results)} rules on file '{file.filename}'.",
        )


class ConformanceSuiteYaml(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    url: str
    rules_lookup_dir: str
    inherit_from: list[str] = Field(
        default_factory=list, description="List of suite names to inherit rules from."
    )
    severity_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Override the severity of inherited rules, keyed by rule reference.",
    )


def load_suite_from_yaml(path: str) -> ConformanceSuiteYaml:
    import yaml

    with open(path) as f:
        data = yaml.safe_load(f)
    return ConformanceSuiteYaml(**data)


def parents_rules(parents: list[str]) -> list[Rule]:
    rules: list[Rule] = []
    for parent_suite_name in parents:
        parent_suite = get_suite(parent_suite_name)
        if parent_suite is None:
            raise ValueError(f"Cannot inherit from suite '{parent_suite_name}': suite not found")
        log.debug(f"Inheriting {len(parent_suite.rules)} rules from suite '{parent_suite_name}'")
        rules.extend(parent_suite.rules)
    return rules


class _ConformanceSuiteProtocolCtor:
    def __init__(
        self,
        name: str,
        rules_lookup_dir: str,
        inherit_from: list[str] | None = None,
        severity_overrides: dict[str, str] | None = None,
        **kwargs,
    ):
        self.kwargs = kwargs
        self.name = name
        self.rules_lookup_dir = rules_lookup_dir
        self.inherit_from = inherit_from or []
        self.severity_overrides = severity_overrides or {}

    def _parse_overrides(self) -> dict[str, Severity]:
        parsed: dict[str, Severity] = {}
        for reference, value in self.severity_overrides.items():
            try:
                parsed[reference] = Severity(value)
            except ValueError as error:
                allowed = ", ".join(level.value for level in Severity)
                raise ValueError(
                    f"Invalid severity '{value}' for rule '{reference}' in "
                    f"severity_overrides of suite '{self.name}'; expected one of: {allowed}"
                ) from error
        return parsed

    def __call__(self) -> ConformanceSuite:
        inherited_rules = parents_rules(self.inherit_from)
        if self.severity_overrides:
            inherited_rules = list(
                apply_severity_overrides(inherited_rules, self._parse_overrides())
            )

        load_rules_from_dir(self.rules_lookup_dir)
        own_rules = get_rules_for_suite(self.name)

        return ConformanceSuite(**self.kwargs, name=self.name, rules=inherited_rules + own_rules)


SUITES = {}


def register_suite(
    description: str,
    url: str,
    name: str,
    rules_lookup_dir: str,
    alternative_names: list[str] | None = None,
    inherit_from: list[str] | None = None,
    severity_overrides: dict[str, str] | None = None,
) -> _ConformanceSuiteProtocolCtor:
    ctor = _ConformanceSuiteProtocolCtor(
        description=description,
        url=url,
        name=name,
        rules_lookup_dir=rules_lookup_dir,
        inherit_from=inherit_from,
        severity_overrides=severity_overrides,
    )
    SUITES[name] = ctor
    if alternative_names:
        for alt_name in alternative_names:
            SUITES[alt_name] = ctor
    return ctor


def get_suite(name: str) -> ConformanceSuite | None:
    if name not in SUITES:
        load_suite_from_dir(_SUITES_DIR, name)
    if ctor := SUITES.get(name):
        return ctor()
    return None


def list_loaded_suites() -> list[str]:
    return list(SUITES.keys())


def list_all_suites() -> list[str]:
    return [
        entry.name
        for entry in _SUITES_DIR.iterdir()
        if entry.is_dir() and not entry.name.startswith("_")
    ]
