# Output Improvements Design

## Goal

Rework the console output to be useful for scientists and calibration code authors. Current output is too verbose (shows all passing checks), exposes internal implementation details (assertion class names, raw paths), and lacks a summary. Adopt conventions from established code linters (ruff, eslint, clippy).

## Approach

Add a **transform pipeline** between validation and reporting. The rule engine stays untouched. A new intermediate `Issue` dataclass provides a flat, pre-processed view of findings that any formatter can consume.

```
ValidationResultGroup → flatten() → [Issue] → filter() → [Issue] → format()
```

## 1. Issue Data Structure

```python
@dataclass
class Issue:
    rule_id: str           # "ISTP-GA-004"
    rule_name: str         # "LogicalFileIdFormat"
    severity: Severity     # ERROR, WARNING, INFO, SKIPPED
    passed: bool           # True = check passed
    message: str           # Human-readable message
    variable: str | None   # "B", "Epoch", None (for global attributes)
    attribute: str | None  # "CATDESC", "Logical_file_id", None
    raw_path: str          # Original path for debugging
```

`variable` and `attribute` are parsed from the raw path:
- `variables/{var}/attributes/{attr}/...` → `variable=var, attribute=attr`
- `variables/{var}/...` → `variable=var, attribute=None`
- `attributes/{attr}/...` → `variable=None, attribute=attr`
- Anything else → `variable=None, attribute=None`

## 2. Transform Pipeline

**`flatten(result_tree: ValidationResultGroup) -> list[Issue]`**
- Recursively walks the tree, collecting leaf `ValidationResult` nodes
- Carries `rule_id` and `rule_name` down from parent `ValidationResultGroup` nodes
- Parses each result's `target` path into `variable`/`attribute` fields

**`filter_issues(issues: list[Issue], verbosity: Verbosity) -> list[Issue]`**
- `Verbosity.NORMAL` (default): keep only failed ERROR + WARNING
- `Verbosity.ALL`: keep everything including passed/skipped/info

## 3. Output Formats

### Flat (default: `--format flat`)

One line per issue, color-coded via Rich:

```
ERROR [ISTP-GA-004] Logical_file_id: value "solo_L2_..." doesn't match expected format
WARN  [ISTP-VA-008] Variable 'QUALITY_FLAG', LABLAXIS: length 12 exceeds maximum 10

solo_l2_rpw-lfr-surv-swf-b_20220221_v02.cdf [ISTP]: 2 errors, 3 warnings (48 passed)
```

### Grouped (`--format grouped`)

Issues grouped by variable/global attribute:

```
Global attribute 'Logical_file_id':
  ERROR [ISTP-GA-004] value "solo_L2_..." doesn't match expected format

Variable 'QUALITY_FLAG':
  WARN  [ISTP-VA-008] LABLAXIS: length 12 exceeds maximum 10

solo_l2_rpw-lfr-surv-swf-b_20220221_v02.cdf [ISTP]: 2 errors, 3 warnings (48 passed)
```

### Tree (`--format tree`)

Existing Rich tree output, preserved for backward compatibility. With `--all`, shows everything (current behavior). Without `--all`, applies severity filtering.

### Summary Line

Always shown: `{filename} [{suite}]: {N} errors, {N} warnings ({N} passed)`

## 4. CLI Changes

| Flag | Description |
|------|-------------|
| `--format flat\|grouped\|tree` | Output format (default: `flat`) |
| `--all` | Show all checks including passed/skipped/info |

Exit codes unchanged:
- Exit 1 on any ERROR-level failure
- Exit 0 otherwise
- `--strict` makes warnings exit 1 too

## 5. Message Improvements

- YAML rules can provide a `message` field with f-string-style interpolation: `"Variable '{variable}': LABLAXIS is {length} chars (max {max})"`
- The presentation layer translates raw paths to human-readable locations (done in `flatten()`)
- Assertions without a custom `message` keep their auto-generated text, with path cleanup by the formatter

## 6. File Changes

| File | Change |
|------|--------|
| `src/astralint/reports/transform.py` | **New** — `Issue`, `flatten()`, `filter_issues()`, path parsing |
| `src/astralint/reports/flat.py` | **New** — flat formatter |
| `src/astralint/reports/grouped.py` | **New** — grouped formatter |
| `src/astralint/reports/__init__.py` | Update dispatcher to route `flat`/`grouped`/`tree` |
| `src/astralint/reports/console.py` | Keep as `tree` format, add severity filtering for `--all` |
| `src/astralint/astralint.py` | Add `--format` and `--all` flags |
| `src/astralint/config/` | Add format/verbosity to config model |
