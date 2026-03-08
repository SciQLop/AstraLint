# Jinja2 Message Templates for Assertions

## Goal

Make assertion messages human-readable at the source. Today, messages embed raw internal paths (`"Value at path 'variables/B/attributes/CATDESC/values/0' does not match pattern '...'"`) and the `target` field stores the same raw path. The report layer should only need to flatten, filter, and display — not rewrite messages.

## Approach

Every assertion renders its message through Jinja2. Each assertion type defines a **default template** and a **context dict**. YAML rules can override the template via the `message` field. Rendering happens in `single_assertion()` — the message is already a finished string when `ValidationResult` is created.

```
YAML rule (optional message template)
        ↓
Assertion.single_assertion()
        ↓
render_message(template, context) → string
        ↓
ValidationResult(message=string, target=clean_target)
```

## 1. Shared Rendering Helper

New helper in `assertions/base.py`:

```python
from jinja2 import Environment

_env = Environment()

def render_message(template: str, context: dict) -> str:
    return _env.from_string(template).render(context)
```

## 2. Context Variables

**Universal context** (provided by `BaseAssertion.evaluate()` to all assertions via path parsing):

| Variable | Type | Description |
|----------|------|-------------|
| `value` | `Any` | The matched value |
| `variable` | `str | None` | Variable name parsed from path |
| `attribute` | `str | None` | Attribute name parsed from path |
| `path` | `str` | The raw resolved path (for debugging) |

**Per-assertion context** (added by each assertion type):

| Assertion | Extra context |
|-----------|--------------|
| `matches` | `pattern` |
| `comparison` | `operator`, `expected` |
| `compare_to` | `operator`, `other_value`, `other_path` + captures |
| `range` | `min`, `max` |
| `length` | `length`, `min`, `max`, `expected` |
| `is_type` | `expected_type`, `actual_type` |
| `contains_keys` | `keys`, `missing_keys` |
| `in` / `not_in` | `values` |
| `requires` | `key` |
| `array_shape` | `expected_shape`, `actual_shape` |
| `reference_variable` | `expected_variable` |

## 3. Default Templates

Each assertion type defines `_default_pass_template` and `_default_fail_template` as class attributes.

| Assertion | Fail template | Pass template |
|-----------|--------------|---------------|
| `exists` | `"{{ attribute or path }} does not exist"` | `"{{ attribute or path }} exists"` |
| `not_exists` | `"{{ attribute or path }} exists but should not"` | `"{{ attribute or path }} does not exist as expected"` |
| `matches` | `"'{{ value }}' does not match pattern '{{ pattern }}'"` | `"'{{ value }}' matches pattern '{{ pattern }}'"` |
| `comparison` | `"{{ value }} does not satisfy {{ operator }} {{ expected }}"` | `"{{ value }} satisfies {{ operator }} {{ expected }}"` |
| `range` | `"{{ value }} is not within range [{{ min }}, {{ max }}]"` | `"{{ value }} is within range [{{ min }}, {{ max }}]"` |
| `length` | `"length {{ length }} is not within expected bounds"` | `"length {{ length }} is within expected bounds"` |
| `not_empty` | `"{{ attribute or path }} is empty"` | `"{{ attribute or path }} is not empty"` |
| `is_type` | `"type is '{{ actual_type }}', expected '{{ expected_type }}'"` | `"type is '{{ expected_type }}' as expected"` |
| `contains_keys` | `"missing keys: {{ missing_keys | join(', ') }}"` | `"all required keys present"` |
| `in` | `"'{{ value }}' is not in the expected values"` | `"'{{ value }}' is in the expected values"` |
| `not_in` | `"'{{ value }}' is in the disallowed values"` | `"'{{ value }}' is not in the disallowed values"` |
| `requires` | `"missing required key '{{ key }}'"` | `"required key '{{ key }}' present"` |
| `array_shape` | `"shape {{ actual_shape }} does not match expected {{ expected_shape }}"` | `"shape matches expected {{ expected_shape }}"` |
| `reference_variable` | `"references undefined variable '{{ value }}'"` | `"correctly references variable '{{ value }}'"` |

Combination assertions (`all_of`, `any_of`, `not`, `if_then`, etc.) keep simple auto-generated messages — they wrap other assertions and their messages are secondary.

## 4. Target Field Cleanup

The `target` field on `ValidationResult` is cleaned up to be human-readable:

| Raw path | Clean target |
|----------|-------------|
| `variables/B/attributes/CATDESC/values/0` | `B/CATDESC` |
| `variables/Epoch/data_type` | `Epoch` |
| `attributes/Logical_source/values/0` | `Logical_source` |
| `attributes` | (empty) |

A `clean_target(raw_path: str) -> str` helper in `assertions/base.py` handles this. Same logic as the previous plan's `parse_path()`, but applied at the source.

## 5. YAML Rule Override

Rules can provide a custom Jinja2 template in `message`:

```yaml
- check: matches
  path: attributes/Logical_source/values/0
  pattern: "^[a-z][a-z0-9_]*$"
  message: "Logical_source '{{ value }}' must be lowercase with underscores"
```

When `message` is non-empty, it replaces the default template. The same context dict is available.

## 6. What Does NOT Change

- `ValidationResult` / `ValidationResultGroup` Pydantic models — same fields, same types
- Rule engine, path resolution, suite orchestration — untouched
- Report layer gets the same tree of results, but with better strings

## 7. File Changes

| File | Change |
|------|--------|
| `src/astralint/base/yaml_rules/assertions/base.py` | Add `render_message()`, `clean_target()`, update `BaseAssertion.evaluate()` to provide universal context |
| `src/astralint/base/yaml_rules/assertions/exists.py` | Default templates + context |
| `src/astralint/base/yaml_rules/assertions/comparisons.py` | Default templates + context |
| `src/astralint/base/yaml_rules/assertions/compare_to.py` | Default templates + context |
| `src/astralint/base/yaml_rules/assertions/matches.py` | Default templates + context |
| `src/astralint/base/yaml_rules/assertions/is_type.py` | Default templates + context |
| `src/astralint/base/yaml_rules/assertions/collections.py` | Default templates + context for length, not_empty, contains_keys, in, not_in, requires, array_shape |
| `src/astralint/base/yaml_rules/assertions/relatioship.py` | Default templates + context |
| `src/astralint/base/yaml_rules/assertions/combinations.py` | Minor cleanup of messages (no templates needed) |
| Tests for each assertion type | Update expected messages |

## 8. Incremental Steps

Each assertion type is an independent commit. Order:

1. `base.py` — add `render_message()` and `clean_target()` helpers
2. `exists.py` — simplest assertion, validates the pattern
3. `matches.py`, `comparisons.py`, `collections.py`, `is_type.py` — one at a time
4. `compare_to.py` — most complex (captures)
5. `combinations.py` — light cleanup
6. `relatioship.py` — last
