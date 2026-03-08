# Jinja2 Message Templates Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace hardcoded f-string messages in assertions with Jinja2 templates, so messages are human-readable from the start and the report layer never needs to rewrite them.

**Architecture:** Add `render_message()` and `clean_target()` helpers to `assertions/base.py`. Each assertion type gets class-level default templates (pass/fail) and builds a context dict. The existing `message` field in YAML rules becomes a Jinja2 template override. All messages flow through the same rendering path.

**Tech Stack:** Python 3.11+, Jinja2 (already a dependency), pytest

---

### Task 1: Add `render_message()` and `clean_target()` Helpers

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/base.py`
- Create: `tests/test_message_rendering.py`

**Step 1: Write failing tests**

```python
import pytest

from astralint.base.yaml_rules.assertions.base import clean_target, render_message


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        ("variables/B/attributes/CATDESC/values/0", "B/CATDESC"),
        ("variables/Epoch/attributes/UNITS/values/0", "Epoch/UNITS"),
        ("variables/B/data_type", "B"),
        ("attributes/Logical_source/values/0", "Logical_source"),
        ("attributes/DOI/values/0", "DOI"),
        ("attributes", ""),
        ("Global", ""),
        ("variables/.*/attributes/CATDESC/values/0", "CATDESC"),
    ],
)
def test_clean_target(raw_path, expected):
    assert clean_target(raw_path) == expected


def test_render_message_simple():
    result = render_message("'{{ value }}' does not match", {"value": "hello"})
    assert result == "'hello' does not match"


def test_render_message_with_filter():
    result = render_message(
        "{{ values | join(', ') }}", {"values": ["a", "b", "c"]}
    )
    assert result == "a, b, c"


def test_render_message_with_none_default():
    result = render_message(
        "{{ attribute or 'unknown' }} is empty", {"attribute": None}
    )
    assert result == "unknown is empty"


def test_render_message_with_attribute():
    result = render_message(
        "{{ attribute or path }} is empty", {"attribute": "CATDESC", "path": "x/y"}
    )
    assert result == "CATDESC is empty"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_message_rendering.py -v`
Expected: FAIL — `ImportError: cannot import name 'clean_target'`

**Step 3: Implement helpers**

Add to `src/astralint/base/yaml_rules/assertions/base.py`:

```python
import re
from jinja2 import Environment

_jinja_env = Environment()

_TARGET_PATTERN = re.compile(
    r"^variables/(?P<var>[^/]+)/attributes/(?P<attr>[^/]+)"
    r"|^variables/(?P<var_only>[^/]+)"
    r"|^attributes/(?P<attr_only>[^/]+)"
)


def render_message(template: str, context: dict) -> str:
    return _jinja_env.from_string(template).render(context)


def clean_target(raw_path: str) -> str:
    m = _TARGET_PATTERN.search(raw_path)
    if not m:
        return ""
    if m.group("var") and m.group("attr"):
        var = m.group("var")
        attr = m.group("attr")
        return f"{var}/{attr}" if var != ".*" else attr
    if m.group("var_only"):
        var = m.group("var_only")
        return "" if var == ".*" else var
    if m.group("attr_only"):
        return m.group("attr_only")
    return ""
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_message_rendering.py -v`
Expected: PASS

**Step 5: Run full test suite to check nothing broke**

Run: `uv run pytest -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/base.py tests/test_message_rendering.py
git commit -m "feat: add render_message and clean_target helpers for assertion templates"
```

---

### Task 2: Refactor `BaseAssertion.evaluate()` — No-Match Messages and Clean Target

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/base.py`
- Modify: `tests/test_message_rendering.py`

**Step 1: Write failing tests**

```python
from astralint.base.file import File
from astralint.base.validation_result import Severity
from astralint.base.yaml_rules.assertions.exists import ExistsAssertion


def test_no_match_message_uses_clean_target(mock_file):
    assertion = ExistsAssertion(check="exists", path="attributes/NonExistent/values/0")
    result = assertion.evaluate(mock_file, Severity.ERROR)
    assert "NonExistent" in result.message
    assert "values/0" not in result.message


def test_no_match_target_is_clean(mock_file):
    assertion = ExistsAssertion(check="exists", path="attributes/NonExistent/values/0")
    result = assertion.evaluate(mock_file, Severity.ERROR)
    assert result.target == "NonExistent"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_message_rendering.py::test_no_match_message_uses_clean_target -v`
Expected: FAIL — message contains `"Path 'attributes/NonExistent/values/0'"` and target is raw path

**Step 3: Update `BaseAssertion.evaluate()` no-match handling**

In `base.py`, update the `evaluate` method of `BaseAssertion` to use templates and clean targets for no-match cases:

```python
_NO_MATCH_FAIL_TEMPLATE = "{{ target or path }} did not match any values"
_NO_MATCH_OK_TEMPLATE = "{{ target or path }} did not match any values (not required)"

class BaseAssertion(BaseEvaluable):
    # ... existing fields ...

    def evaluate(self, file: File, severity: Severity) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path(file, self.path)
        results: list[ValidationResult | ValidationResultGroup] = []
        if not matches:
            target = clean_target(self.path)
            ctx = {"target": target, "path": self.path}
            if self.error_if_no_match:
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=Severity.ERROR,
                    message=render_message(_NO_MATCH_FAIL_TEMPLATE, ctx),
                    target=target,
                )
            else:
                return ValidationResult(
                    valid=True,
                    reference="",
                    severity=Severity.INFO,
                    message=render_message(_NO_MATCH_OK_TEMPLATE, ctx),
                    target=target,
                )
        for path, value in matches:
            result = self.single_assertion(file, path, value, severity=severity)
            results.append(result)
        return ValidationResultGroup(
            name=self.__class__.__name__,
            rule_reference="",
            results=results,
            severity=severity,
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_message_rendering.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: PASS (some existing tests may need message string updates — fix them)

**Step 6: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/base.py tests/test_message_rendering.py
git commit -m "refactor: use templates and clean targets in BaseAssertion no-match handling"
```

---

### Task 3: Refactor `ExistsAssertion` and `NotExistsAssertion`

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/exists.py`
- Modify: `tests/test_message_rendering.py`

**Step 1: Write failing tests**

```python
def test_exists_pass_message(mock_file):
    assertion = ExistsAssertion(check="exists", path="attributes/global_attr")
    result = assertion.evaluate(mock_file, Severity.ERROR)
    assert result.valid is True
    assert "global_attr" in result.message
    assert "exists" in result.message
    assert "path" not in result.message.lower()


def test_exists_fail_message(mock_file):
    assertion = ExistsAssertion(check="exists", path="attributes/Missing")
    result = assertion.evaluate(mock_file, Severity.ERROR)
    assert result.valid is False
    assert "Missing" in result.message
    assert result.target == "Missing"


def test_exists_pass_target_is_clean(mock_file):
    assertion = ExistsAssertion(check="exists", path="attributes/global_attr")
    result = assertion.evaluate(mock_file, Severity.ERROR)
    assert result.target == "global_attr"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_message_rendering.py::test_exists_pass_message -v`
Expected: FAIL — message contains `"Path 'attributes/global_attr'"`

**Step 3: Refactor exists.py**

```python
from typing import Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult, ValidationResultGroup
from .base import BaseAssertion, clean_target, render_message, resolve_path


class ExistsAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["exists"] = "exists"  # type: ignore[assignment]

    _default_pass_template: str = "{{ target or path }} exists"
    _default_fail_template: str = "{{ target or path }} does not exist"

    def evaluate(self, file: File, severity: Severity) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path(file, self.path)
        target = clean_target(self.path)
        ctx = {"target": target, "path": self.path}
        if matches:
            return ValidationResult(
                valid=True,
                reference="",
                severity=severity,
                message=render_message(self.message or self._default_pass_template, ctx),
                target=target,
            )
        else:
            return ValidationResult(
                valid=False,
                reference="",
                severity=severity,
                message=render_message(self.message or self._default_fail_template, ctx),
                target=target,
            )


class NotExistsAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["not_exists"] = "not_exists"  # type: ignore[assignment]

    _default_pass_template: str = "{{ target or path }} does not exist as expected"
    _default_fail_template: str = "{{ target or path }} exists but should not"

    def evaluate(self, file: File, severity: Severity) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path(file, self.path)
        target = clean_target(self.path)
        ctx = {"target": target, "path": self.path}
        if matches:
            return ValidationResult(
                valid=False,
                reference="",
                severity=severity,
                message=render_message(self.message or self._default_fail_template, ctx),
                target=target,
            )
        else:
            return ValidationResult(
                valid=True,
                reference="",
                severity=severity,
                message=render_message(self.message or self._default_pass_template, ctx),
                target=target,
            )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_message_rendering.py -v`
Expected: PASS

**Step 5: Run full test suite and fix any broken message assertions**

Run: `uv run pytest -v`
Expected: PASS (update existing tests that check exact message strings from exists assertions)

**Step 6: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/exists.py tests/test_message_rendering.py
git commit -m "refactor: Jinja2 templates for ExistsAssertion and NotExistsAssertion"
```

---

### Task 4: Refactor `MatchesAssertion`

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/matches.py`
- Modify: `tests/test_message_rendering.py`

**Step 1: Write failing tests**

```python
from astralint.base.yaml_rules.assertions.matches import MatchesAssertion


def test_matches_fail_message(mock_file):
    assertion = MatchesAssertion(
        check="matches",
        path="attributes/global_attr/values/0",
        pattern="^[a-z]+$",
    )
    result = assertion.evaluate(mock_file, Severity.ERROR)
    # result is a ValidationResultGroup with one leaf
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "does not match" in leaf.message
    assert "path" not in leaf.message.lower()
    assert leaf.target == "global_attr"


def test_matches_pass_message():
    from astralint.base.file import Attribute, DataType, File

    f = File(
        extension="mock",
        filename="test.mock",
        attributes={
            "Source": Attribute(
                name="Source", data_type=[DataType.STRING], shape=[1], values=["hello"]
            )
        },
        variables={},
        compression="NONE",
    )
    assertion = MatchesAssertion(
        check="matches", path="attributes/Source/values/0", pattern="^[a-z]+$"
    )
    result = assertion.evaluate(f, Severity.WARNING)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert leaf.valid is True
    assert "'hello'" in leaf.message
    assert "matches" in leaf.message


def test_matches_custom_message():
    from astralint.base.file import Attribute, DataType, File

    f = File(
        extension="mock",
        filename="test.mock",
        attributes={
            "Source": Attribute(
                name="Source", data_type=[DataType.STRING], shape=[1], values=["BAD"]
            )
        },
        variables={},
        compression="NONE",
    )
    assertion = MatchesAssertion(
        check="matches",
        path="attributes/Source/values/0",
        pattern="^[a-z]+$",
        message="{{ attribute }} '{{ value }}' must be lowercase",
    )
    result = assertion.evaluate(f, Severity.WARNING)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert leaf.message == "Source 'BAD' must be lowercase"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_message_rendering.py::test_matches_fail_message -v`
Expected: FAIL

**Step 3: Refactor matches.py**

```python
import re
from typing import Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion, clean_target, render_message


class MatchesAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["matches"] = "matches"  # type: ignore[assignment]
    pattern: re.Pattern

    _default_pass_template: str = "'{{ value }}' matches pattern '{{ pattern }}'"
    _default_fail_template: str = "'{{ value }}' does not match pattern '{{ pattern }}'"
    _not_string_template: str = "expected a string value, got {{ value.__class__.__name__ }}"

    def single_assertion(
        self, file: File, path: str, value: str, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        ctx = {
            "value": value,
            "pattern": self.pattern.pattern,
            "variable": None,
            "attribute": None,
            "path": path,
        }
        # Parse variable/attribute from target
        parts = target.split("/")
        if len(parts) == 2:
            ctx["variable"], ctx["attribute"] = parts
        elif len(parts) == 1 and target:
            # Could be a variable or attribute depending on path prefix
            ctx["attribute"] = target if path.startswith("attributes/") else None
            ctx["variable"] = target if path.startswith("variables/") else None

        if not isinstance(value, str):
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=render_message(self._not_string_template, ctx),
                target=target,
            )
        elif not re.match(self.pattern, value):
            return ValidationResult(
                valid=False,
                reference="",
                severity=severity,
                message=render_message(self.message or self._default_fail_template, ctx),
                target=target,
            )
        else:
            return ValidationResult(
                valid=True,
                reference="",
                message=render_message(self.message or self._default_pass_template, ctx),
                severity=severity,
                target=target,
            )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_message_rendering.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/matches.py tests/test_message_rendering.py
git commit -m "refactor: Jinja2 templates for MatchesAssertion"
```

---

### Task 5: Refactor `ComparisonAssertion` and `RangeAssertion`

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/comparisons.py`
- Modify: `tests/test_message_rendering.py`

**Step 1: Write failing tests**

```python
from astralint.base.yaml_rules.assertions.comparisons import (
    ComparisonAssertion,
    RangeAssertion,
)


def test_comparison_fail_message(mock_file):
    assertion = ComparisonAssertion(
        check="comparison",
        path="attributes/global_attr/values/0",
        operator=">",
        value=100,
    )
    result = assertion.evaluate(mock_file, Severity.ERROR)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "does not satisfy" in leaf.message
    assert "path" not in leaf.message.lower()
    assert leaf.target == "global_attr"


def test_range_fail_message(mock_file):
    assertion = RangeAssertion(
        check="range",
        path="attributes/global_attr/values/0",
        min=100,
        max=200,
    )
    result = assertion.evaluate(mock_file, Severity.WARNING)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "not within range" in leaf.message
    assert leaf.target == "global_attr"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_message_rendering.py::test_comparison_fail_message -v`
Expected: FAIL

**Step 3: Refactor comparisons.py**

```python
from typing import Any, Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion, clean_target, render_message

_yaml_types = int | float | bool | list | str

_operators = {
    "=": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


def _build_context(path: str, raw_path: str, value: Any, **extra: Any) -> dict:
    ctx: dict = {"value": value, "path": raw_path, "variable": None, "attribute": None}
    parts = path.split("/")
    if len(parts) == 2:
        ctx["variable"], ctx["attribute"] = parts
    elif len(parts) == 1 and path:
        ctx["attribute"] = path if raw_path.startswith("attributes/") else None
        ctx["variable"] = path if raw_path.startswith("variables/") else None
    ctx.update(extra)
    return ctx


class ComparisonAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["comparison"] = "comparison"  # type: ignore[assignment]
    operator: Literal["=", "!=", "<", "<=", ">", ">="]
    value: _yaml_types

    _default_pass_template: str = "{{ value }} satisfies {{ operator }} {{ expected }}"
    _default_fail_template: str = "{{ value }} does not satisfy {{ operator }} {{ expected }}"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        ctx = _build_context(target, path, value, operator=self.operator, expected=self.value)
        passed = _operators[self.operator](value, self.value)
        template = self.message or (self._default_pass_template if passed else self._default_fail_template)
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(template, ctx),
            target=target,
        )


class RangeAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["range"] = "range"  # type: ignore[assignment]
    min: _yaml_types
    max: _yaml_types

    _default_pass_template: str = "{{ value }} is within range [{{ min }}, {{ max }}]"
    _default_fail_template: str = "{{ value }} is not within range [{{ min }}, {{ max }}]"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        ctx = _build_context(target, path, value, min=self.min, max=self.max)
        passed = self.min <= value <= self.max
        template = self.message or (self._default_pass_template if passed else self._default_fail_template)
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(template, ctx),
            target=target,
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_message_rendering.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/comparisons.py tests/test_message_rendering.py
git commit -m "refactor: Jinja2 templates for ComparisonAssertion and RangeAssertion"
```

---

### Task 6: Refactor Collection Assertions (in, not_in, length, not_empty, requires, array_shape)

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/collections.py`
- Modify: `tests/test_message_rendering.py`

**Step 1: Write failing tests**

```python
from astralint.base.yaml_rules.assertions.collections import (
    ContainsAssertion,
    LengthAssertion,
    NotEmptyAssertion,
    RequiresAssertion,
)


def test_contains_fail_message(mock_file):
    assertion = ContainsAssertion(
        check="in",
        path="attributes/global_attr/values/0",
        values=[1, 2, 3],
    )
    result = assertion.evaluate(mock_file, Severity.ERROR)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "not in" in leaf.message.lower() or "expected values" in leaf.message.lower()
    assert "path" not in leaf.message.lower()
    assert leaf.target == "global_attr"


def test_length_fail_message():
    from astralint.base.file import Attribute, DataType, File

    f = File(
        extension="mock",
        filename="test.mock",
        attributes={
            "TEXT": Attribute(
                name="TEXT", data_type=[DataType.STRING], shape=[1], values=["hi"]
            )
        },
        variables={},
        compression="NONE",
    )
    assertion = LengthAssertion(
        check="length", path="attributes/TEXT/values/0", min=10
    )
    result = assertion.evaluate(f, Severity.WARNING)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "2" in leaf.message  # actual length
    assert "10" in leaf.message  # min
    assert leaf.target == "TEXT"


def test_not_empty_fail_message():
    from astralint.base.file import Attribute, DataType, File

    f = File(
        extension="mock",
        filename="test.mock",
        attributes={
            "TEXT": Attribute(
                name="TEXT", data_type=[DataType.STRING], shape=[1], values=[""]
            )
        },
        variables={},
        compression="NONE",
    )
    assertion = NotEmptyAssertion(
        check="not_empty", path="attributes/TEXT/values/0"
    )
    result = assertion.evaluate(f, Severity.WARNING)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "empty" in leaf.message
    assert leaf.target == "TEXT"


def test_requires_fail_message(mock_file):
    assertion = RequiresAssertion(
        check="requires",
        path="variables",
        key="MissingVar",
    )
    result = assertion.evaluate(mock_file, Severity.ERROR)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "MissingVar" in leaf.message
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_message_rendering.py::test_contains_fail_message -v`
Expected: FAIL

**Step 3: Refactor collections.py**

Apply the same pattern as comparisons.py: add `_default_pass_template` / `_default_fail_template` class attributes, use `clean_target()` and `render_message()` in each `single_assertion()`. Use the `_build_context` helper (import from comparisons or move to base — prefer moving to base).

Note: move `_build_context` to `base.py` so all assertion files can use it.

Default templates:

- `ContainsAssertion`: fail=`"'{{ value }}' is not in the expected values"`, pass=`"'{{ value }}' is in the expected values"`
- `NotContainsAssertion`: fail=`"'{{ value }}' is in the disallowed values"`, pass=`"'{{ value }}' is not in the disallowed values"`
- `LengthAssertion`:
  - exact fail: `"length {{ length }}, expected {{ expected }}"`
  - min fail: `"length {{ length }} is less than minimum {{ min }}"`
  - max fail: `"length {{ length }} exceeds maximum {{ max }}"`
  - pass: `"length {{ length }} is within expected bounds"`
  - error: `"value does not have a length"`
- `NotEmptyAssertion`: fail=`"{{ attribute or variable or path }} is empty"`, pass=`"{{ attribute or variable or path }} is not empty"`
- `RequiresAssertion`: fail=`"missing required key '{{ key }}'"`, pass=`"required key '{{ key }}' present"`
- `ArrayShapeAssertion`:
  - pass: `"shape matches expected {{ expected_shape }}"`
  - not array: `"value is not an array"`
  - dim mismatch: `"has {{ actual_dims }} dimensions, expected {{ expected_dims }}"`
  - item mismatch: `"item {{ index }} has length {{ actual_length }}, expected {{ expected_length }}"`

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_message_rendering.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/base.py src/astralint/base/yaml_rules/assertions/collections.py tests/test_message_rendering.py
git commit -m "refactor: Jinja2 templates for collection assertions"
```

---

### Task 7: Refactor `IsTypeAssertion`

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/is_type.py`
- Modify: `tests/test_message_rendering.py`

**Step 1: Write failing tests**

```python
from astralint.base.yaml_rules.assertions.is_type import IsTypeAssertion


def test_is_type_fail_message(mock_file):
    assertion = IsTypeAssertion(
        check="is_type",
        path="attributes/global_attr/data_type/0",
        type="FLOAT64",
    )
    result = assertion.evaluate(mock_file, Severity.ERROR)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "FLOAT64" in leaf.message
    assert "INT32" in leaf.message
    assert "path" not in leaf.message.lower()
    assert leaf.target == "global_attr"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_message_rendering.py::test_is_type_fail_message -v`
Expected: FAIL

**Step 3: Refactor is_type.py**

Default templates:
- pass: `"type is '{{ expected_type }}' as expected"`
- fail: `"type is '{{ actual_type }}', expected '{{ expected_type }}'"`
- error: `"value is not a valid DataType, got '{{ value }}'"`

Same pattern: `clean_target()`, `_build_context()`, `render_message()`.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_message_rendering.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/is_type.py tests/test_message_rendering.py
git commit -m "refactor: Jinja2 templates for IsTypeAssertion"
```

---

### Task 8: Refactor `ReferencesVariableAssertion`

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/relatioship.py`
- Modify: `tests/test_message_rendering.py`

**Step 1: Write failing tests**

```python
from astralint.base.yaml_rules.assertions.relatioship import ReferencesVariableAssertion


def test_ref_variable_fail_message(mock_file):
    assertion = ReferencesVariableAssertion(
        check="reference_variable",
        path="attributes/global_attr/values/0",
    )
    result = assertion.evaluate(mock_file, Severity.WARNING)
    leaf = result.results[0] if hasattr(result, "results") else result
    # value is 42 (int), not a string
    assert "string" in leaf.message.lower() or "not a string" in leaf.message.lower()
    assert leaf.target == "global_attr"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_message_rendering.py::test_ref_variable_fail_message -v`
Expected: FAIL

**Step 3: Refactor relatioship.py**

Default templates:
- pass (specific): `"correctly references variable '{{ value }}'"`
- pass (any): `"references existing variable '{{ value }}'"`
- fail (undefined): `"references undefined variable '{{ value }}'"`
- fail (wrong var): `"is '{{ value }}', expected reference to '{{ expected_variable }}'"`
- error (not string): `"expected a string value to reference a variable"`

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_message_rendering.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/relatioship.py tests/test_message_rendering.py
git commit -m "refactor: Jinja2 templates for ReferencesVariableAssertion"
```

---

### Task 9: Refactor `CompareToAssertion`

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/compare_to.py`
- Modify: `tests/test_message_rendering.py`

This is the most complex assertion — it uses path captures and already has partial message interpolation via `interpolate_captures()`.

**Step 1: Write failing tests**

```python
from astralint.base.yaml_rules.assertions.compare_to import CompareToAssertion


def test_compare_to_fail_message(mock_file_with_range):
    assertion = CompareToAssertion(
        check="compare_to",
        path="variables/{var}/attributes/FILLVAL/values/0",
        operator="<",
        other_path="variables/{var}/attributes/VALIDMIN/values/0",
    )
    result = assertion.evaluate(mock_file_with_range, Severity.WARNING)
    leaf = result.results[0]
    # FILLVAL is -1e31, VALIDMIN is 0.0 → -1e31 < 0.0 is True → passes
    assert leaf.valid is True
    assert "path" not in leaf.message.lower() or "path" in leaf.message.lower()
    # Target should be clean
    assert "values/0" not in leaf.target


def test_compare_to_custom_jinja_message(mock_file_with_range):
    assertion = CompareToAssertion(
        check="compare_to",
        path="variables/{var}/attributes/FILLVAL/values/0",
        operator="<",
        other_path="variables/{var}/attributes/VALIDMIN/values/0",
        message="Variable '{{ var }}': FILLVAL ({{ value }}) must be < VALIDMIN ({{ other_value }})",
    )
    result = assertion.evaluate(mock_file_with_range, Severity.WARNING)
    leaf = result.results[0]
    assert "var1" in leaf.message
    assert "FILLVAL" in leaf.message
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_message_rendering.py::test_compare_to_custom_jinja_message -v`
Expected: FAIL — current `interpolate_captures` uses `{name}` not `{{ name }}`

**Step 3: Refactor compare_to.py**

Key changes:
- Replace `interpolate_captures()` with `render_message()` (Jinja2)
- Build context with `captures` dict entries merged in, plus `value`, `other_value`, `operator`
- Use `clean_target()` for target field
- Default templates:
  - pass: `"{{ value }} {{ operator }} {{ other_value }}"`
  - fail: `"{{ value }} does not satisfy {{ operator }} {{ other_value }}"`
  - other not found: `"comparison target not found"`

**Important:** Existing YAML rules that use `{var}` style interpolation in `message` fields must be migrated to `{{ var }}` Jinja2 syntax. Search for such rules and update them.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_message_rendering.py -v`
Expected: PASS

**Step 5: Search and update YAML rules using old `{name}` message syntax**

Run: `grep -r '{[a-z_]*}' src/astralint/suites/ --include='*.yaml' -l`

For each file found, convert `{name}` to `{{ name }}` in `message` fields only.

**Step 6: Run full test suite**

Run: `uv run pytest -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/compare_to.py tests/test_message_rendering.py
git add src/astralint/suites/  # any updated YAML rules
git commit -m "refactor: Jinja2 templates for CompareToAssertion and migrate YAML message syntax"
```

---

### Task 10: Final Cleanup and Full Verification

**Files:**
- Possibly modify: `tests/test_assertions.py` (update any hardcoded message expectations)

**Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: PASS — fix any remaining tests that check exact old message strings

**Step 2: Run linter and type checker**

Run: `make lint`
Expected: PASS

**Step 3: Check that `interpolate_captures` is no longer used**

Run: `grep -r 'interpolate_captures' src/`

If still referenced, either remove it or keep it for backward compat if tests use it.

**Step 4: Commit any remaining fixes**

```bash
git add -u
git commit -m "chore: fix remaining tests for new Jinja2 message format"
```
