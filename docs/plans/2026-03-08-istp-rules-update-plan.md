# ISTP Rules Update Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update the ISTP conformance suite to match the ISTP Metadata Guidelines spec exactly, including extending the assertion system with path captures and `compare_to`.

**Architecture:** Fix-in-place approach. Extend `resolve_path` with `{name}` / `{name:pattern}` capture syntax. Add `CompareToAssertion` in a new file. Edit existing YAML rules and add new ones. TDD throughout.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, YAML rules, regex path system.

---

### Task 1: Path Capture — Parsing

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/base.py`
- Test: `tests/test_assertions.py`

**Step 1: Write failing tests for capture parsing**

```python
def test_parse_captures_simple():
    from astralint.base.yaml_rules.assertions.base import parse_captures
    pattern, captures = parse_captures("variables/{var}/attributes/FILLVAL")
    assert pattern == "variables/(.*)/attributes/FILLVAL"
    assert captures == {"var": 0}


def test_parse_captures_with_regex():
    from astralint.base.yaml_rules.assertions.base import parse_captures
    pattern, captures = parse_captures("variables/{var:LFR_.*}/attributes")
    assert pattern == "variables/(LFR_.*)/attributes"
    assert captures == {"var": 0}


def test_parse_captures_multiple():
    from astralint.base.yaml_rules.assertions.base import parse_captures
    pattern, captures = parse_captures("{a}/attributes/{b:X.*}")
    assert pattern == "(.*)/attributes/(X.*)"
    assert captures == {"a": 0, "b": 1}


def test_parse_captures_no_captures():
    from astralint.base.yaml_rules.assertions.base import parse_captures
    pattern, captures = parse_captures("variables/.*/attributes")
    assert pattern == "variables/.*/attributes"
    assert captures == {}
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_assertions.py -k "test_parse_captures" -v`
Expected: FAIL (ImportError, `parse_captures` not found)

**Step 3: Implement `parse_captures` in `base.py`**

Add this function before `resolve_path`:

```python
import re

_CAPTURE_RE = re.compile(r"\{(\w+)(?::([^}]+))?\}")

def parse_captures(path: str) -> tuple[str, dict[str, int]]:
    """Parse {name} and {name:pattern} captures from a path.

    Returns (regex_pattern, {name: group_index}) where group_index is 0-based.
    """
    captures: dict[str, int] = {}
    group_index = 0

    def replacer(match: re.Match) -> str:
        nonlocal group_index
        name = match.group(1)
        pattern = match.group(2) or ".*"
        captures[name] = group_index
        group_index += 1
        return f"({pattern})"

    regex_pattern = _CAPTURE_RE.sub(replacer, path)
    return regex_pattern, captures
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_assertions.py -k "test_parse_captures" -v`
Expected: PASS

**Step 5: Commit**

```
feat: add parse_captures for {name} and {name:pattern} path syntax
```

---

### Task 2: Path Capture — Integration with `resolve_path`

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/base.py`
- Test: `tests/test_assertions.py`

**Step 1: Write failing tests**

```python
def test_resolve_path_with_captures(mock_file):
    from astralint.base.yaml_rules.assertions.base import resolve_path_with_captures
    matches = resolve_path_with_captures(mock_file, "variables/{var}/data_type")
    assert len(matches) >= 1
    path, value, captures = matches[0]
    assert "var" in captures
    assert captures["var"] == "var1"


def test_resolve_path_with_captures_no_captures(mock_file):
    from astralint.base.yaml_rules.assertions.base import resolve_path_with_captures
    matches = resolve_path_with_captures(mock_file, "variables/.*/data_type")
    assert len(matches) >= 1
    path, value, captures = matches[0]
    assert captures == {}
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_assertions.py -k "test_resolve_path_with_captures" -v`
Expected: FAIL

**Step 3: Implement `resolve_path_with_captures`**

Add to `base.py`:

```python
def resolve_path_with_captures(
    obj: Any, path: str
) -> list[tuple[str, Any, dict[str, str]]]:
    """Like resolve_path but extracts named captures from matched paths.

    Returns list of (matched_path, value, {capture_name: captured_value}).
    """
    regex_pattern, capture_names = parse_captures(path)
    flattened = flatten_object(obj)
    rx = re.compile("^" + regex_pattern + "$")
    results = []
    for flat_path, value in flattened:
        m = rx.match(flat_path)
        if m:
            captured = {name: m.group(idx + 1) for name, idx in capture_names.items()}
            results.append((flat_path, value, captured))
    return results
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_assertions.py -k "test_resolve_path_with_captures" -v`
Expected: PASS

**Step 5: Commit**

```
feat: add resolve_path_with_captures for named path captures
```

---

### Task 3: Path Capture — Message Interpolation

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/base.py`
- Test: `tests/test_assertions.py`

**Step 1: Write failing test**

```python
def test_interpolate_captures():
    from astralint.base.yaml_rules.assertions.base import interpolate_captures
    msg = interpolate_captures("Variable '{var}' has bad FILLVAL", {"var": "Epoch"})
    assert msg == "Variable 'Epoch' has bad FILLVAL"


def test_interpolate_captures_no_captures():
    from astralint.base.yaml_rules.assertions.base import interpolate_captures
    msg = interpolate_captures("No captures here", {})
    assert msg == "No captures here"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_assertions.py -k "test_interpolate_captures" -v`
Expected: FAIL

**Step 3: Implement `interpolate_captures`**

```python
def interpolate_captures(template: str, captures: dict[str, str]) -> str:
    """Substitute {name} placeholders in a template with captured values."""
    result = template
    for name, value in captures.items():
        result = result.replace("{" + name + "}", value)
    return result
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_assertions.py -k "test_interpolate_captures" -v`
Expected: PASS

**Step 5: Commit**

```
feat: add interpolate_captures for message templating
```

---

### Task 4: `compare_to` Assertion

**Files:**
- Create: `src/astralint/base/yaml_rules/assertions/compare_to.py`
- Modify: `src/astralint/base/yaml_rules/assertions/__init__.py`
- Test: `tests/test_assertions.py`

**Step 1: Write failing tests**

The `mock_file` fixture needs variables with FILLVAL, VALIDMIN, VALIDMAX. Add a richer fixture first:

```python
@pytest.fixture
def mock_file_with_range():
    return File(
        extension="cdf",
        filename="test.cdf",
        compression="NONE",
        attributes={},
        variables={
            "var1": Variable(
                name="var1",
                shape=[10],
                attributes={
                    "FILLVAL": Attribute(name="FILLVAL", data_type=[DataType.FLOAT64], shape=[1], values=[-1e31]),
                    "VALIDMIN": Attribute(name="VALIDMIN", data_type=[DataType.FLOAT64], shape=[1], values=[0.0]),
                    "VALIDMAX": Attribute(name="VALIDMAX", data_type=[DataType.FLOAT64], shape=[1], values=[100.0]),
                },
                data_type=DataType.FLOAT64,
                compression="NONE",
                record_variance=True,
            ),
        },
    )


def test_compare_to_less_than_passes(mock_file_with_range):
    rule_yaml = """
name: test
description: test
url: "https://test"
reference: TEST-001
severity: ERROR
suite: TEST
assertions:
    - path: "variables/{var}/attributes/FILLVAL/values/0"
      check: compare_to
      operator: "<"
      other_path: "variables/{var}/attributes/VALIDMIN/values/0"
      message: "Variable '{var}': FILLVAL must be less than VALIDMIN"
    """
    rule = YamlRule(**safe_load(rule_yaml))
    result = rule.check(mock_file_with_range)
    assert result.valid  # -1e31 < 0.0


def test_compare_to_fails_when_in_range(mock_file_with_range):
    """FILLVAL=50 is NOT less than VALIDMIN=0, so this should fail."""
    mock_file_with_range.variables["var1"].attributes["FILLVAL"] = Attribute(
        name="FILLVAL", data_type=[DataType.FLOAT64], shape=[1], values=[50.0]
    )
    rule_yaml = """
name: test
description: test
url: "https://test"
reference: TEST-001
severity: ERROR
suite: TEST
assertions:
    - path: "variables/{var}/attributes/FILLVAL/values/0"
      check: compare_to
      operator: "<"
      other_path: "variables/{var}/attributes/VALIDMIN/values/0"
      message: "Variable '{var}': FILLVAL must be less than VALIDMIN"
    """
    rule = YamlRule(**safe_load(rule_yaml))
    result = rule.check(mock_file_with_range)
    assert not result.valid


def test_compare_to_message_interpolation(mock_file_with_range):
    rule_yaml = """
name: test
description: test
url: "https://test"
reference: TEST-001
severity: ERROR
suite: TEST
assertions:
    - path: "variables/{var}/attributes/FILLVAL/values/0"
      check: compare_to
      operator: "<"
      other_path: "variables/{var}/attributes/VALIDMIN/values/0"
      message: "Variable '{var}': FILLVAL must be less than VALIDMIN"
    """
    rule = YamlRule(**safe_load(rule_yaml))
    result = rule.check(mock_file_with_range)
    # Check that the message contains the interpolated variable name
    assert "var1" in str(result)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_assertions.py -k "test_compare_to" -v`
Expected: FAIL

**Step 3: Implement `CompareToAssertion`**

Create `src/astralint/base/yaml_rules/assertions/compare_to.py`:

```python
from typing import Any, Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult, ValidationResultGroup
from .base import (
    BaseEvaluable,
    interpolate_captures,
    resolve_path,
    resolve_path_with_captures,
)

_operators = {
    "=": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


class CompareToAssertion(BaseEvaluable):
    model_config = ConfigDict(frozen=True)
    check: Literal["compare_to"] = "compare_to"  # type: ignore[assignment]
    path: str
    operator: Literal["=", "!=", "<", "<=", ">", ">="]
    other_path: str
    error_if_no_match: bool = True
    message: str = ""

    def evaluate(
        self, file: File, severity: Severity
    ) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path_with_captures(file, self.path)
        if not matches:
            if self.error_if_no_match:
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=Severity.ERROR,
                    message=f"Path '{self.path}' did not match any values.",
                    target=self.path,
                )
            return ValidationResult(
                valid=True,
                reference="",
                severity=Severity.INFO,
                message=f"Path '{self.path}' did not match any values, but that's okay.",
                target=self.path,
            )

        results: list[ValidationResult | ValidationResultGroup] = []
        for path, value, captures in matches:
            resolved_other = interpolate_captures(self.other_path, captures)
            other_matches = resolve_path(file, resolved_other)
            if not other_matches:
                results.append(
                    ValidationResult(
                        valid=False,
                        reference="",
                        severity=severity,
                        message=interpolate_captures(
                            f"Comparison target path '{resolved_other}' not found.",
                            captures,
                        ),
                        target=path,
                    )
                )
                continue
            other_value = other_matches[0][1]
            msg = interpolate_captures(self.message, captures)
            try:
                passed = _operators[self.operator](value, other_value)
            except TypeError:
                passed = False
            results.append(
                ValidationResult(
                    valid=passed,
                    reference="",
                    severity=severity,
                    message=msg
                    or f"'{path}' {self.operator} '{resolved_other}': {value} {self.operator} {other_value} -> {'pass' if passed else 'fail'}",
                    target=path,
                )
            )
        return ValidationResultGroup(
            name="CompareToAssertion",
            rule_reference="",
            results=results,
            severity=severity,
        )
```

**Step 4: Register in `__init__.py`**

Add to `src/astralint/base/yaml_rules/assertions/__init__.py`:

```python
from .compare_to import CompareToAssertion
```

And add `"CompareToAssertion"` to `__all__`.

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_assertions.py -k "test_compare_to" -v`
Expected: PASS

**Step 6: Commit**

```
feat: add compare_to assertion with path capture support
```

---

### Task 5: Fix Global Attribute Rules

**Files:**
- Modify: `src/astralint/suites/ISTP/rules/GlobalAttributes/MandatoryGlobalAttributes.yaml`
- Modify: `src/astralint/suites/ISTP/rules/GlobalAttributes/RecommendedGlobalAttributes.yaml`
- Modify: `src/astralint/suites/ISTP/rules/GlobalAttributes/DisciplineValues.yaml`
- Modify: `src/astralint/suites/ISTP/rules/GlobalAttributes/InstrumentTypeValues.yaml`

**Step 1: Edit MandatoryGlobalAttributes.yaml**

Remove `Discipline` and `Project` from the `keys` list. The remaining 12 keys should be:
`Data_type`, `Data_version`, `Descriptor`, `Instrument_type`, `Logical_file_id`, `Logical_source`, `Logical_source_description`, `Mission_group`, `PI_affiliation`, `PI_name`, `Source_name`, `TEXT`.

**Step 2: Edit RecommendedGlobalAttributes.yaml**

Add `Discipline`, `Project`, `DOI`, `spase_DatasetResourceID` to the `keys` list.

**Step 3: Edit DisciplineValues.yaml**

Replace the values list with exactly these 5:
- `"Solar Physics>Heliospheric Physics"`
- `"Space Physics>Interplanetary Studies"`
- `"Space Physics>Magnetospheric Science"`
- `"Space Physics>Ionospheric Science"`
- `"Space Physics>Astrophysics Science"`

**Step 4: Edit InstrumentTypeValues.yaml**

Replace the values list with all 17 spec values:
- `"Activity Indices"`
- `"Electric Fields (space)"`
- `"Engineering"`
- `"Ephemeris/Attitude/Ancillary"`
- `"Ground-Based HF-Radars"`
- `"Ground-Based Imagers"`
- `"Ground-Based Magnetometers, Riometers, Sounders"`
- `"Ground-Based VLF/ELF/ULF, Photometers"`
- `"Housekeeping"`
- `"Imaging and Remote Sensing (ITM/Earth)"`
- `"Imaging and Remote Sensing (Magnetosphere/Earth)"`
- `"Imaging and Remote Sensing (Sun)"`
- `"Magnetic Fields (Balloon)"`
- `"Magnetic Fields (space)"`
- `"Particles (space)"`
- `"Plasma and Solar Wind"`
- `"Radio and Plasma Waves (space)"`

**Step 5: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: PASS (or controlled failures from integration tests using real files)

**Step 6: Commit**

```
fix: correct global attribute rules to match ISTP spec
```

---

### Task 6: Fix Variable Attribute Rules

**Files:**
- Modify: `src/astralint/suites/ISTP/rules/VariableAttributes/DataVariableAttributes.yaml`
- Modify: `src/astralint/suites/ISTP/rules/VariableAttributes/SupportDataVariableAttributes.yaml`
- Modify: `src/astralint/suites/ISTP/rules/VariableAttributes/MandatoryVariableAttributes.yaml`

**Step 1: Edit DataVariableAttributes.yaml**

The `if_then` block currently requires `LABLAXIS` and `UNITS` directly. Change to use `any_of`:
- Replace the `LABLAXIS` exists check with `any_of(exists LABLAXIS, exists LABL_PTR_1)`
- Replace the `UNITS` exists check with `any_of(exists UNITS, exists UNIT_PTR)`

Example YAML for the LABLAXIS part:
```yaml
- check: any_of
  message: "Data variable must have LABLAXIS or LABL_PTR_1"
  assertions:
    - path: "../LABLAXIS"
      check: exists
      error_if_no_match: false
      message: ""
    - path: "../LABL_PTR_1"
      check: exists
      error_if_no_match: false
      message: ""
```

Note: The exact path syntax depends on how `if_then` nests paths. Review the current rule's structure and adapt. The paths inside the `then` block of an `if_then` are absolute, so use `variables/.*/attributes/LABLAXIS`.

**Step 2: Edit SupportDataVariableAttributes.yaml**

Restructure to:
- Add `any_of(LABLAXIS, LABL_PTR_1)` check
- Change `FORMAT` to `any_of(FORMAT, FORM_PTR)`
- Add conditional `DEPEND_0` requirement: `if_then(record_variance=true, requires DEPEND_0)`
- Make `FILLVAL` conditional on record variance

**Step 3: Edit MandatoryVariableAttributes.yaml**

Change the `FILLVAL` requirement from unconditional `contains_keys` to a conditional check: if record_variance is true, then FILLVAL must exist. Keep CATDESC, FIELDNAM, VAR_TYPE as unconditional.

**Step 4: Run tests**

Run: `uv run pytest tests/ -v`
Expected: PASS

**Step 5: Commit**

```
fix: correct variable attribute rules for LABLAXIS/UNITS alternatives and record variance
```

---

### Task 7: Fix Length and Severity Rules

**Files:**
- Modify: `src/astralint/suites/ISTP/rules/VariableAttributes/CatdescLength.yaml`
- Modify: `src/astralint/suites/ISTP/rules/VariableAttributes/FieldnamLength.yaml`
- Modify: `src/astralint/suites/ISTP/rules/VariableAttributes/LablaxisLength.yaml`
- Modify: `src/astralint/suites/ISTP/rules/Variables/EpochVariable.yaml`
- Modify: `src/astralint/suites/ISTP/rules/Variables/EpochAttributes.yaml`

**Step 1: Edit CatdescLength.yaml**

Split into two assertions:
- WARNING severity rule: `length max: 80` (preferred)
- Add a second rule file `CatdescMaxLength.yaml` with ERROR severity: `length max: 120` (hard max)

OR keep in one file with two assertions at different severities. Since YAML rules have a single `severity` field per rule, create a separate file for the hard limit.

**Step 2: Edit FieldnamLength.yaml**

Same pattern: WARNING at 30 stays, add `FieldnamMaxLength.yaml` with ERROR at 50.

**Step 3: Edit LablaxisLength.yaml**

Same pattern: WARNING at 10 stays, add `LablaxisMaxLength.yaml` with ERROR at 20.

**Step 4: Edit EpochVariable.yaml**

Change severity to WARNING. Add a separate check (possibly a new rule file) that validates at least one variable is referenced via `DEPEND_0` somewhere.

**Step 5: Edit EpochAttributes.yaml**

Split the rule: keep `CATDESC`, `FIELDNAM`, `FILLVAL`, `LABLAXIS`, `UNITS`, `VALIDMIN`, `VALIDMAX`, `VAR_TYPE` as ERROR. Move `MONOTON`, `TIME_BASE`, `TIME_SCALE` to a new `EpochRecommendedAttributes.yaml` with WARNING severity.

**Step 6: Run tests**

Run: `uv run pytest tests/ -v`
Expected: PASS

**Step 7: Commit**

```
fix: separate preferred/hard limits and correct epoch attribute severities
```

---

### Task 8: Add New Rules — Pointer References

**Files:**
- Create: `src/astralint/suites/ISTP/rules/VariableAttributes/UnitPtrReferences.yaml`
- Create: `src/astralint/suites/ISTP/rules/VariableAttributes/FormPtrReferences.yaml`
- Create: `src/astralint/suites/ISTP/rules/VariableAttributes/ScalPtrReferences.yaml`

**Step 1: Create UnitPtrReferences.yaml**

```yaml
name: UnitPtrReferences
description: "UNIT_PTR must reference an existing variable"
url: "https://spdf.gsfc.nasa.gov/istp_guide/vattributes.html#UNIT_PTR"
reference: "ISTP-VA-016"
severity: ERROR
suite: ISTP

assertions:
  - path: "variables/.*/attributes/UNIT_PTR/values/[0-9]*"
    check: reference_variable
    error_if_no_match: false
    message: "UNIT_PTR must reference an existing variable"
```

**Step 2: Create FormPtrReferences.yaml** (same pattern with FORM_PTR)

**Step 3: Create ScalPtrReferences.yaml** (same pattern with SCAL_PTR)

**Step 4: Run tests**

Run: `uv run pytest tests/ -v`
Expected: PASS

**Step 5: Commit**

```
feat: add reference validation for UNIT_PTR, FORM_PTR, SCAL_PTR
```

---

### Task 9: Add New Rules — MetadataVariableAttributes

**Files:**
- Create: `src/astralint/suites/ISTP/rules/VariableAttributes/MetadataVariableAttributes.yaml`

**Step 1: Create MetadataVariableAttributes.yaml**

```yaml
name: MetadataVariableAttributes
description: "Metadata variables must have required attributes per ISTP spec"
url: "https://spdf.gsfc.nasa.gov/istp_guide/variables.html#Metadata"
reference: "ISTP-VA-015"
severity: ERROR
suite: ISTP

assertions:
  - path: "variables/.*/attributes/VAR_TYPE/values/[0-9]*"
    check: if_then
    if:
      path: "variables/.*/attributes/VAR_TYPE/values/[0-9]*"
      check: comparison
      operator: "="
      value: "metadata"
    then:
      check: all_of
      assertions:
        - path: "variables/.*/attributes"
          check: contains_keys
          keys:
            - CATDESC
            - FIELDNAM
            - VAR_TYPE
          message: "Metadata variable missing required attributes"
        - path: "variables/.*/attributes"
          check: any_of
          message: "Metadata variable must have FORMAT or FORM_PTR"
          assertions:
            - path: "FORMAT"
              check: exists
              error_if_no_match: false
              message: ""
            - path: "FORM_PTR"
              check: exists
              error_if_no_match: false
              message: ""
```

Note: The exact nesting of paths inside `if_then` needs to match how the current `DataVariableAttributes.yaml` does it. Review that file's structure and replicate the pattern.

**Step 2: Run tests**

Run: `uv run pytest tests/ -v`
Expected: PASS

**Step 3: Commit**

```
feat: add metadata variable attributes rule
```

---

### Task 10: Add New Rules — Global Attribute Validation

**Files:**
- Create: `src/astralint/suites/ISTP/rules/GlobalAttributes/DOIFormat.yaml`
- Create: `src/astralint/suites/ISTP/rules/GlobalAttributes/GenerationDateFormat.yaml`
- Create: `src/astralint/suites/ISTP/rules/GlobalAttributes/LinkCountConsistency.yaml`

**Step 1: Create DOIFormat.yaml**

```yaml
name: DOIFormat
description: "DOI must use the standard https://doi.org/ format"
url: "https://spdf.gsfc.nasa.gov/istp_guide/gattributes.html#DOI"
reference: "ISTP-GA-014"
severity: WARNING
suite: ISTP

assertions:
  - path: "attributes/DOI/values/[0-9]*"
    check: matches
    error_if_no_match: false
    pattern: "^https://doi\\.org/.+/.+$"
    message: "DOI must be of the form https://doi.org/PREFIX/SUFFIX"
```

**Step 2: Create GenerationDateFormat.yaml**

```yaml
name: GenerationDateFormat
description: "Generation_date must use yyyymmdd format"
url: "https://spdf.gsfc.nasa.gov/istp_guide/gattributes.html#Generation_date"
reference: "ISTP-GA-015"
severity: WARNING
suite: ISTP

assertions:
  - path: "attributes/Generation_date/values/[0-9]*"
    check: matches
    error_if_no_match: false
    pattern: "^\\d{8}$"
    message: "Generation_date must use yyyymmdd format"
```

**Step 3: Create LinkCountConsistency.yaml**

This is tricky — we need to compare lengths across attributes. This could use `compare_to` on the length/shape of the attributes, or it might need a dedicated approach. If the `Attribute.shape` or length of `values` list can be accessed via path, use `compare_to`:

```yaml
name: LinkCountConsistency
description: "HTTP_LINK, LINK_TEXT, and LINK_TITLE must have the same number of entries"
url: "https://spdf.gsfc.nasa.gov/istp_guide/gattributes.html#LINK_TEXT"
reference: "ISTP-GA-013"
severity: ERROR
suite: ISTP

assertions:
  - path: "attributes/HTTP_LINK/shape/0"
    check: compare_to
    error_if_no_match: false
    operator: "="
    other_path: "attributes/LINK_TEXT/shape/0"
    message: "HTTP_LINK and LINK_TEXT must have the same number of entries"
  - path: "attributes/HTTP_LINK/shape/0"
    check: compare_to
    error_if_no_match: false
    operator: "="
    other_path: "attributes/LINK_TITLE/shape/0"
    message: "HTTP_LINK and LINK_TITLE must have the same number of entries"
```

**Step 4: Run tests**

Run: `uv run pytest tests/ -v`
Expected: PASS

**Step 5: Commit**

```
feat: add DOI format, generation date format, and link count consistency rules
```

---

### Task 11: Add New Rules — FillvalOutsideRange and ProposalAttributes

**Files:**
- Create: `src/astralint/suites/ISTP/rules/VariableAttributes/FillvalOutsideRange.yaml`
- Create: `src/astralint/suites/ISTP/rules/VariableAttributes/ProposalAttributes.yaml`

**Step 1: Create FillvalOutsideRange.yaml**

```yaml
name: FillvalOutsideRange
description: "FILLVAL must be outside the [VALIDMIN, VALIDMAX] range"
url: "https://spdf.gsfc.nasa.gov/istp_guide/vattributes.html#FILLVAL"
reference: "ISTP-VA-019"
severity: ERROR
suite: ISTP

assertions:
  - path: "variables/{var}/attributes/FILLVAL/values/0"
    check: any_of
    error_if_no_match: false
    message: "Variable '{var}': FILLVAL must be outside [VALIDMIN, VALIDMAX] range"
    assertions:
      - path: "variables/{var}/attributes/FILLVAL/values/0"
        check: compare_to
        operator: "<"
        other_path: "variables/{var}/attributes/VALIDMIN/values/0"
        error_if_no_match: false
        message: ""
      - path: "variables/{var}/attributes/FILLVAL/values/0"
        check: compare_to
        operator: ">"
        other_path: "variables/{var}/attributes/VALIDMAX/values/0"
        error_if_no_match: false
        message: ""
```

**Step 2: Create ProposalAttributes.yaml**

```yaml
name: ProposalAttributes
description: "ISTP proposal attributes (informational)"
url: "https://spdf.gsfc.nasa.gov/istp_guide/vattributes.html"
reference: "ISTP-INFO-001"
severity: INFO
suite: ISTP

assertions:
  - path: "variables/.*/attributes"
    check: contains_keys
    error_if_no_match: false
    keys:
      - COORDINATE_SYSTEM
    message: "PROPOSAL: COORDINATE_SYSTEM attribute is available for vectors/tensors"
  - path: "attributes"
    check: contains_keys
    error_if_no_match: false
    keys:
      - Data_processing_level
    message: "PROPOSAL: Data_processing_level attribute is available"
```

**Step 3: Run tests**

Run: `uv run pytest tests/ -v`
Expected: PASS

**Step 4: Commit**

```
feat: add FILLVAL range validation and proposal attributes info rules
```

---

### Task 12: Update Documentation

**Files:**
- Modify: `docs/assertions.md`

**Step 1: Add `compare_to` section to assertions.md**

Add after the `reference_variable` section:

````markdown
### `compare_to`

Compare a value at one path against a value at another path in the same file.

**Operators:** `=`, `!=`, `<`, `<=`, `>`, `>=`

```yaml
# FILLVAL must be less than VALIDMIN
- path: "variables/{var}/attributes/FILLVAL/values/0"
  check: compare_to
  operator: "<"
  other_path: "variables/{var}/attributes/VALIDMIN/values/0"
  message: "Variable '{var}': FILLVAL must be less than VALIDMIN"
```
````

**Step 2: Add Path Captures section**

Add a new section under "Path Patterns":

````markdown
### Named Captures

Capture path segments for reuse in `other_path` and `message` fields:

| Syntax | Description |
|--------|-------------|
| `{name}` | Capture segment, matches `.*` |
| `{name:pattern}` | Capture segment, matches custom regex |

```yaml
# Capture variable name, use in other_path and message
- path: "variables/{var}/attributes/FILLVAL/values/0"
  check: compare_to
  operator: "<"
  other_path: "variables/{var}/attributes/VALIDMIN/values/0"
  message: "Variable '{var}': FILLVAL must be less than VALIDMIN"

# Capture with custom regex filter
- path: "variables/{var:LFR_.*}/attributes/UNITS/values/0"
  check: not_empty
  message: "LFR variable '{var}' must have non-empty UNITS"
```
````

**Step 3: Commit**

```
docs: add compare_to assertion and path captures to assertions reference
```

---

### Task 13: Run Full Test Suite and Lint

**Step 1: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All PASS

**Step 2: Run linter**

Run: `make lint`
Expected: PASS

**Step 3: Run integration test with real CDF file**

Run: `uv run pytest tests/test_cdf_istp.py -v`
Expected: PASS (results may differ from before due to rule changes — review output)

**Step 4: Final commit if any fixes needed**

```
fix: address lint and test issues from ISTP rules update
```
