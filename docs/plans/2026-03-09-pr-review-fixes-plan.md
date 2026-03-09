# PR Review Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Address all review comments on PR #10 — generalize path captures, add combinator message support, harden template rendering, fix docs.

**Architecture:** Changes center on `base.py` (captures + rendering), `combinations.py` (message field), and docs. Each task is independently testable.

**Tech Stack:** Python 3.11+, Pydantic, Jinja2, pytest

---

### Task 1: Switch `parse_captures` to named regex groups

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/base.py:100-128`
- Modify: `tests/test_assertions.py:18-64`

**Step 1: Update `parse_captures` to emit `(?P<name>...)` named groups**

Replace the current implementation in `base.py`:

```python
def parse_captures(path: str) -> tuple[str, list[str]]:
    """Parse {name} and {name:pattern} captures from a path into a regex pattern and capture names."""
    capture_names: list[str] = []

    def _replace(match: re.Match) -> str:
        name = match.group(1)
        pattern = match.group(2) or "[^/]*"
        capture_names.append(name)
        return f"(?P<{name}>{pattern})"

    regex_pattern = _CAPTURE_RE.sub(_replace, path)
    return regex_pattern, capture_names
```

**Step 2: Update `resolve_path_with_captures` to use `match.group(name)`**

```python
def resolve_path_with_captures(obj: Any, path: str) -> list[tuple[str, Any, dict[str, str]]]:
    """Like resolve_path but extracts captured values from {name} placeholders."""
    pattern, capture_names = parse_captures(path)
    flattened = flatten_object(obj)
    rx = re.compile("^" + pattern + "$")
    results: list[tuple[str, Any, dict[str, str]]] = []
    for flat_path, value in flattened:
        m = rx.match(flat_path)
        if m:
            captured = {name: m.group(name) for name in capture_names}
            results.append((flat_path, value, captured))
    return results
```

**Step 3: Update existing tests for new return type**

In `tests/test_assertions.py`, update tests that check `parse_captures` return value — the second element is now a `list[str]` of names, not a `dict[str, int]` of name→index mappings.

```python
def test_parse_captures_simple():
    pattern, capture_names = parse_captures("variables/{var}/attributes/FILLVAL")
    assert capture_names == ["var"]
    assert "(?P<var>[^/]*)" in pattern

def test_parse_captures_with_regex():
    pattern, capture_names = parse_captures("variables/{var:LFR_.*}/attributes/UNITS")
    assert capture_names == ["var"]
    assert "(?P<var>LFR_.*)" in pattern

def test_parse_captures_multiple():
    pattern, capture_names = parse_captures("variables/{var}/attributes/{attr}")
    assert capture_names == ["var", "attr"]
```

**Step 4: Add test for duplicate capture names**

```python
def test_parse_captures_duplicate_name_raises():
    import re as re_mod
    with pytest.raises(re_mod.error):
        pattern, _ = parse_captures("variables/{var}/other/{var}")
        re_mod.compile("^" + pattern + "$")
```

**Step 5: Add test for custom pattern with inner groups**

```python
def test_parse_captures_inner_groups():
    pattern, capture_names = parse_captures("variables/{var:(LFR|HFR)_.*}/attributes/UNITS")
    assert capture_names == ["var"]
    rx = re.compile("^" + pattern + "$")
    m = rx.match("variables/LFR_test/attributes/UNITS")
    assert m is not None
    assert m.group("var") == "LFR_test"
```

**Step 6: Run tests**

Run: `uv run pytest tests/test_assertions.py -k "parse_captures or resolve_path_with_captures" -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/base.py tests/test_assertions.py
git commit -m "refactor: use named regex groups in parse_captures"
```

---

### Task 2: Generalize path captures to all assertions

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/base.py:160-192`
- Modify: `tests/test_message_rendering.py`

**Step 1: Write failing test — captures available in any assertion's message**

Add to `tests/test_message_rendering.py`:

```python
def test_exists_assertion_with_path_captures(mock_file_with_range: Any) -> None:
    """Path captures like {var} should work in any assertion, not just compare_to."""
    assertion = ExistsAssertion(
        check="exists",
        path="variables/{var}/attributes/VALIDMIN",
        message="{% if valid %}{{ var }} has VALIDMIN{% else %}{{ var }} missing VALIDMIN{% endif %}",
    )
    result = assertion.evaluate(mock_file_with_range, Severity.WARNING)
    leaf = _leaf(result)
    assert "var1" in leaf.message
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_message_rendering.py::test_exists_assertion_with_path_captures -v`
Expected: FAIL (captures not available in context)

**Step 3: Update `BaseAssertion.evaluate()` to use `resolve_path_with_captures`**

In `base.py`, change `BaseAssertion.evaluate()`:

```python
def evaluate(self, file: File, severity: Severity) -> ValidationResult | ValidationResultGroup:
    matches = resolve_path_with_captures(file, self.path)
    results: list[ValidationResult | ValidationResultGroup] = []
    if not matches:
        target = clean_target(self.path)
        valid = not self.error_if_no_match
        ctx = {"target": target, "path": self.path, "valid": valid}
        return ValidationResult(
            valid=valid,
            reference="",
            severity=Severity.ERROR if not valid else Severity.INFO,
            message=render_message(_NO_MATCH_TEMPLATE, ctx),
            target=target,
        )
    for path, value, captures in matches:
        result = self.single_assertion(file, path, value, severity=severity, captures=captures)
        results.append(result)
    return ValidationResultGroup(
        name=self.__class__.__name__,
        rule_reference="",
        results=results,
        severity=severity,
    )
```

**Step 4: Update `single_assertion` signature and all subclasses**

Add `captures: dict[str, str] | None = None` parameter to `BaseAssertion.single_assertion` and all concrete assertion classes. In each `single_assertion`, merge captures into context:

```python
def single_assertion(
    self, file: File, path: str, value: Any, severity: Severity, captures: dict[str, str] | None = None
) -> ValidationResult:
    target = clean_target(path)
    ctx = build_context(target, path, value, valid=..., **(captures or {}))
    ...
```

The affected assertion files are:
- `exists.py`
- `comparison.py`
- `range_check.py`
- `is_type.py`
- `matches.py`
- `contains.py`
- `not_contains.py`
- `in_set.py`
- `not_in_set.py`
- `length.py`
- `not_empty.py`
- `requires.py`
- `contains_keys.py`
- `reference_variable.py`
- `array_shape.py`

For each, add `captures: dict[str, str] | None = None` to `single_assertion` and pass `**(captures or {})` into `build_context`.

**Step 5: Run test**

Run: `uv run pytest tests/test_message_rendering.py::test_exists_assertion_with_path_captures -v`
Expected: PASS

**Step 6: Run full test suite**

Run: `uv run pytest -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/
git add tests/test_message_rendering.py
git commit -m "feat: generalize path captures to all assertions"
```

---

### Task 3: Add `message` field to combinators

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/combinations.py`
- Modify: `tests/test_assertions.py`

**Step 1: Write failing test — `any_of` with custom message**

Add to `tests/test_assertions.py`:

```python
def test_any_of_custom_message():
    rule_yaml = {
        "check": "any_of",
        "message": "Must have FORMAT or FORM_PTR",
        "assertions": [
            {"path": "variables/.*/attributes/FORMAT", "check": "exists", "error_if_no_match": False, "message": ""},
            {"path": "variables/.*/attributes/FORM_PTR", "check": "exists", "error_if_no_match": False, "message": ""},
        ],
    }
    from pydantic import TypeAdapter
    from astralint.base.yaml_rules.assertions.base import get_assertion_union
    adapter = TypeAdapter(get_assertion_union())
    assertion = adapter.validate_python(rule_yaml)
    # Build a file missing both FORMAT and FORM_PTR
    file = make_file({"variables": {"v1": {"attributes": {"CATDESC": {"values": ["test"]}}}}})
    result = assertion.evaluate(file, Severity.ERROR)
    assert not result.valid
    assert result.message == "Must have FORMAT or FORM_PTR"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_assertions.py::test_any_of_custom_message -v`
Expected: FAIL

**Step 3: Add `message` field to `BaseAssertionGroup`**

In `combinations.py`, import `render_message` from `.base` and add `message` to `BaseAssertionGroup`:

In `base.py`:
```python
class BaseAssertionGroup(BaseEvaluable):
    model_config = ConfigDict(frozen=True)
    assertions: list[Any]
    message: str = Field(default="")
    ...
```

**Step 4: Update each combinator to use `self.message` when set**

For each combinator (`AllOf`, `AnyOf`, `NoneOf`, `OneOf`, `AtLeast`, `AtMost`, `Exactly`), replace hardcoded message strings with a pattern like:

```python
def _result_message(self, valid: bool, default: str) -> str:
    if self.message:
        return render_message(self.message, {"valid": valid})
    return default
```

Add this as a method on `BaseAssertionGroup`. Then in each combinator, replace e.g.:
```python
message="All assertions in 'any_of' failed."
```
with:
```python
message=self._result_message(False, "All assertions in 'any_of' failed.")
```

**Step 5: Run test**

Run: `uv run pytest tests/test_assertions.py::test_any_of_custom_message -v`
Expected: PASS

**Step 6: Add test for combinator without message (default fallback)**

```python
def test_any_of_default_message_when_no_custom():
    rule_yaml = {
        "check": "any_of",
        "assertions": [
            {"path": "variables/.*/attributes/FORMAT", "check": "exists", "error_if_no_match": False, "message": ""},
        ],
    }
    from pydantic import TypeAdapter
    from astralint.base.yaml_rules.assertions.base import get_assertion_union
    adapter = TypeAdapter(get_assertion_union())
    assertion = adapter.validate_python(rule_yaml)
    file = make_file({"variables": {"v1": {"attributes": {"CATDESC": {"values": ["test"]}}}}})
    result = assertion.evaluate(file, Severity.ERROR)
    assert not result.valid
    assert "any_of" in result.message  # default fallback
```

**Step 7: Run full test suite**

Run: `uv run pytest -v`
Expected: All PASS

**Step 8: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/base.py
git add src/astralint/base/yaml_rules/assertions/combinations.py
git add tests/test_assertions.py
git commit -m "feat: add optional message field to combinator assertions"
```

---

### Task 4: Error wrapping in `render_message`

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/base.py:19-20`
- Modify: `tests/test_message_rendering.py`

**Step 1: Write failing test**

```python
def test_render_message_bad_template_does_not_crash() -> None:
    from astralint.base.yaml_rules.assertions.base import render_message
    result = render_message("{% if broken %", {"valid": True})
    assert "[template error" in result

def test_render_message_undefined_variable_does_not_crash() -> None:
    from astralint.base.yaml_rules.assertions.base import render_message
    result = render_message("{{ undefined_var }}", {})
    # Jinja2 default is to render undefined as empty string, so this should work fine
    assert isinstance(result, str)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_message_rendering.py::test_render_message_bad_template_does_not_crash -v`
Expected: FAIL (raises TemplateSyntaxError)

**Step 3: Add error wrapping**

```python
from jinja2 import Environment, TemplateSyntaxError, UndefinedError

def render_message(template: str, context: dict) -> str:
    try:
        return _jinja_env.from_string(template).render(context)
    except (TemplateSyntaxError, UndefinedError) as e:
        return f"[template error: {e}] template: {template}"
```

**Step 4: Run tests**

Run: `uv run pytest tests/test_message_rendering.py -k "render_message" -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/base.py tests/test_message_rendering.py
git commit -m "fix: wrap Jinja2 template errors instead of crashing"
```

---

### Task 5: Sort `missing_keys` in `ContainsKeysAssertion`

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/contains_keys.py:39`
- Modify: `tests/test_message_rendering.py`

**Step 1: Write test for deterministic ordering**

```python
def test_contains_keys_missing_keys_sorted(mock_file: Any) -> None:
    assertion = ContainsKeysAssertion(
        check="contains_keys",
        path="variables/.*/attributes",
        keys=frozenset({"ZEBRA", "APPLE", "MANGO"}),
    )
    result = assertion.evaluate(mock_file, Severity.WARNING)
    leaf = _leaf(result)
    # Missing keys should appear in sorted order
    assert "APPLE" in leaf.message
    idx_a = leaf.message.index("APPLE")
    idx_m = leaf.message.index("MANGO")
    idx_z = leaf.message.index("ZEBRA")
    assert idx_a < idx_m < idx_z
```

**Step 2: Fix in `contains_keys.py`**

Change line 39 from:
```python
missing_keys=missing_keys,
```
to:
```python
missing_keys=sorted(missing_keys),
```

**Step 3: Run tests**

Run: `uv run pytest tests/test_message_rendering.py -k "contains_keys" -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/contains_keys.py tests/test_message_rendering.py
git commit -m "fix: sort missing_keys for deterministic output"
```

---

### Task 6: Fix doc examples and YAML rules

**Files:**
- Modify: `docs/assertions.md` (lines ~281 and ~777)
- Verify: ISTP YAML rules (already use correct Jinja2 syntax in `message`)

**Step 1: Fix `docs/assertions.md` compare_to example**

Change:
```yaml
message: "Variable '{var}': FILLVAL must be less than VALIDMIN"
```
to:
```yaml
message: "Variable '{{ var }}': FILLVAL must be less than VALIDMIN"
```

**Step 2: Fix `docs/assertions.md` named captures examples**

Change:
```yaml
message: "Variable '{var}': FILLVAL must be less than VALIDMIN"
```
to:
```yaml
message: "Variable '{{ var }}': FILLVAL must be less than VALIDMIN"
```

And:
```yaml
message: "LFR variable '{var}' must have non-empty UNITS"
```
to:
```yaml
message: "LFR variable '{{ var }}' must have non-empty UNITS"
```

**Step 3: Update the `not_empty` example to clarify captures work with all assertions**

Since Task 2 generalized captures, this example is now accurate. Just fix the Jinja2 syntax.

**Step 4: Verify YAML rules**

Check that the ISTP YAML rules already use `{{ var }}` (Jinja2) in `message` fields — they do (confirmed in exploration). No changes needed there.

**Step 5: Commit**

```bash
git add docs/assertions.md
git commit -m "docs: fix Jinja2 syntax in message examples"
```

---

### Task 7: Run full suite and lint

**Step 1: Run linter**

Run: `make lint`
Expected: PASS

**Step 2: Run full test suite**

Run: `make test`
Expected: All PASS

**Step 3: Fix any issues found**

If lint or tests fail, fix and commit.
