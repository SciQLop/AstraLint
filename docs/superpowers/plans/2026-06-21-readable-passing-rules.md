# Readable Passing Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make passing rules in the console (`--show-passed`) and HTML reports self-describing — each passing line carries its rule reference and the concrete validated member/value — by preserving combinator member detail in the engine and centralizing the report cleanup.

**Architecture:** Two small engine changes on the success path only (`AllOf` returns its children as a group; `AnyOf` stamps the passing alternative's target/value onto its leaf), plus one shared reporting helper (`reports/_findings.py`) that both the console tree and HTML renderer use to flatten internal wrapper groups, stamp the nearest rule reference onto leaves, and drop pass-path noise leaves. Failure paths are untouched so the resolver contract is preserved.

**Tech Stack:** Python 3.11+, Pydantic models (`ValidationResult` / `ValidationResultGroup`), Jinja2 (HTML templates), Rich (console tree), pytest, uv.

**Spec:** `docs/superpowers/specs/2026-06-21-readable-passing-rules-design.md`

**Conventions:** Tests live flat in `tests/test_*.py`. Run a single test with `uv run pytest tests/test_x.py::test_name -v`. Load + run a suite with `from astralint.base import get_suite, load_file` then `get_suite("ISTP").run(load_file("tests/resources/<name>.cdf"))`. The MMS resource CDF is `tests/resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf`. The data model is structured (not raw strings): `Attribute(name, data_type=[DataType.CHAR], shape=[1], values=[value])`, `Variable(name, attributes={name: Attribute}, compression, data_type, record_variance, shape)`, `File(extension, filename, compression, attributes, variables)` — all importable from `astralint.base.file`. Commit messages end with the Co-Authored-By trailer used in this repo. **Stage only the explicitly named files** — never `git add -A`/`.` (the tree carries untracked throwaways).

---

## File Structure

- `tests/test_failing_leaf_invariance.py` — **new**. Regression guard: the multiset of failing leaves over the MMS resource CDF is pinned, proving the engine changes don't alter failure output (the resolver contract).
- `src/astralint/base/yaml_rules/assertions/combinations.py` — **modify**. Add `_first_pass` helper; change `AllOf.evaluate` (pass path) and `AnyOf.evaluate` (pass path).
- `src/astralint/reports/_findings.py` — **new**. Shared presentation logic: `is_internal_wrapper`, `display_children` (flatten wrappers, stamp reference, drop noise).
- `src/astralint/reports/console.py` — **modify**. `--show-passed` tree (`_render_group`) uses `display_children`; leaves render their (now-stamped) reference.
- `src/astralint/reports/html.py` — **modify**. Replace local `_is_internal_wrapper`/`_display_children` with the shared helper; `RESULT_TEMPLATE` already shows `result.reference`.
- `tests/test_passing_rule_clarity.py` — **new**. End-to-end behavioral tests for both surfaces.

---

## Task 1: Pin failing-leaf output (regression guard, written first)

This test captures the CURRENT failing-leaf set so later engine changes are proven not to alter failures. Write and run it BEFORE any engine change.

**Files:**
- Test: `tests/test_failing_leaf_invariance.py` (create)

- [ ] **Step 1: Write a helper + capture script to print the current failing leaves**

Run this throwaway one-liner to get the current baseline (do NOT commit it):

```bash
uv run python -c "
from astralint.base import get_suite, load_file
from astralint.base import ValidationResult, ValidationResultGroup
def leaves(n):
    if isinstance(n, ValidationResult):
        yield n
    else:
        for c in n.results: yield from leaves(c)
r = get_suite('ISTP').run(load_file('tests/resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf'))
fails = sorted((l.reference, l.target, l.severity.value, l.message) for l in leaves(r) if not l.valid)
print(len(fails))
for f in fails: print(f)
"
```

Expected: a deterministic list (the MMS file's known failures). Copy the printed count and tuples into the test below as `EXPECTED`.

- [ ] **Step 2: Write the guard test using the captured baseline**

```python
# tests/test_failing_leaf_invariance.py
from astralint.base import ValidationResult, ValidationResultGroup, get_suite, load_file

RESOURCE = "tests/resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf"


def _leaves(node):
    if isinstance(node, ValidationResult):
        yield node
    else:
        for child in node.results:
            yield from _leaves(child)


def _failing_signature(node) -> list[tuple[str, str, str, str]]:
    return sorted(
        (leaf.reference, leaf.target, leaf.severity.value, leaf.message)
        for leaf in _leaves(node)
        if not leaf.valid
    )


# Paste the exact tuples printed in Step 1 here.
EXPECTED: list[tuple[str, str, str, str]] = [
    # ("ISTP-VA-...", "<target>", "ERROR", "<message>"),
]


def test_failing_leaves_are_unchanged():
    """The resolver routes on failing-leaf (reference, target, message); this work
    must not change any failing-path output. If this breaks, a pass-path change
    leaked into the failure path."""
    results = get_suite("ISTP").run(load_file(RESOURCE))
    assert _failing_signature(results) == EXPECTED
```

- [ ] **Step 3: Run the guard — it must pass on the unmodified engine**

Run: `uv run pytest tests/test_failing_leaf_invariance.py -v`
Expected: PASS (proves the baseline is captured correctly).

- [ ] **Step 4: Commit**

```bash
git add tests/test_failing_leaf_invariance.py
git commit -m "test: pin failing-leaf output as a regression guard

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `AnyOf` — stamp the passing alternative's target/value

`AnyOf` already renders the rule's own message; it only lacks the concrete target. Add a `_first_pass` helper (also used by Task 3 reasoning) and set `target`/`value` on the passing leaf. Stays one leaf — no count change. Failure path untouched.

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/combinations.py`
- Test: `tests/test_passing_rule_clarity.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_passing_rule_clarity.py
from pydantic import TypeAdapter

from astralint.base.file import Attribute, DataType, File, Variable
from astralint.base.validation_result import Severity
from astralint.base.yaml_rules.assertions.base import get_assertion_union

_adapter = TypeAdapter(get_assertion_union())


def _attr(name: str, value: str) -> Attribute:
    return Attribute(name=name, data_type=[DataType.CHAR], shape=[1], values=[value])


def _file_with_var(attrs: dict[str, str]) -> File:
    return File(
        extension="cdf",
        filename="t.cdf",
        compression="NONE",
        attributes={},
        variables={
            "Bx": Variable(
                name="Bx",
                attributes={k: _attr(k, v) for k, v in attrs.items()},
                compression="NONE",
                data_type=DataType.FLOAT32,
                record_variance=True,
                shape=[10],
            )
        },
    )


def test_any_of_pass_reports_the_passing_alternative_target():
    assertion = _adapter.validate_python(
        {
            "check": "any_of",
            "message": "must have LABLAXIS or LABL_PTR_1",
            "assertions": [
                {"check": "exists", "path": "variables/Bx/attributes/LABLAXIS", "message": ""},
                {"check": "exists", "path": "variables/Bx/attributes/LABL_PTR_1", "message": ""},
            ],
        }
    )
    result = assertion.evaluate(_file_with_var({"LABLAXIS": "B"}), Severity.ERROR)
    assert result.valid
    assert result.message == "must have LABLAXIS or LABL_PTR_1"
    assert "LABLAXIS" in result.target
```

(If the `File`/`Variable` construction differs from the codebase, mirror the construction used in `tests/test_assertions.py` — check it first.)

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_passing_rule_clarity.py::test_any_of_pass_reports_the_passing_alternative_target -v`
Expected: FAIL (`result.target` is empty today).

- [ ] **Step 3: Add `_first_pass` and update `AnyOf.evaluate`**

Add this helper next to `_first_failure` in `combinations.py`:

```python
def _first_pass(
    result: ValidationResult | ValidationResultGroup,
) -> tuple[str, str] | None:
    """The (target, value) of the first genuinely-passing leaf under ``result``.
    Lets ``any_of`` name which alternative satisfied it."""
    if isinstance(result, ValidationResultGroup):
        for child in result.results:
            found = _first_pass(child)
            if found is not None:
                return found
        return None
    if result.valid and result.severity != Severity.SKIPPED:
        return result.target, result.value
    return None
```

In `AnyOf.evaluate`, replace the success-path `return` (the `if result.valid:` block) with:

```python
            if result.valid:
                target, value = _first_pass(result) or ("", "")
                return ValidationResult(
                    valid=True,
                    reference="",
                    severity=severity,
                    message=self._result_message(
                        True, "At least one assertion in 'any_of' passed successfully."
                    ),
                    target=target,
                    value=value,
                )
```

Leave the all-failed path below it exactly as-is.

- [ ] **Step 4: Run the test (and the guard) to verify pass**

Run: `uv run pytest tests/test_passing_rule_clarity.py tests/test_failing_leaf_invariance.py -v`
Expected: PASS (the new test passes; the guard still passes — failure path unchanged).

- [ ] **Step 5: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/combinations.py tests/test_passing_rule_clarity.py
git commit -m "feat(engine): any_of names the passing alternative's target

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `AllOf` — preserve member detail on the pass path

On success, `AllOf` returns a `ValidationResultGroup` of its sub-results (like `IfThen`) instead of one generic leaf, so each validated member survives to the report. Failure path (first-failure leaf the resolver routes on) is unchanged.

**Files:**
- Modify: `src/astralint/base/yaml_rules/assertions/combinations.py`
- Test: `tests/test_passing_rule_clarity.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_passing_rule_clarity.py`:

```python
from astralint.base import ValidationResult, ValidationResultGroup


def _leaf_messages(node):
    if isinstance(node, ValidationResult):
        return [node.message]
    out = []
    for child in node.results:
        out += _leaf_messages(child)
    return out


def test_all_of_pass_preserves_each_member():
    assertion = _adapter.validate_python(
        {
            "check": "all_of",
            "assertions": [
                {
                    "check": "exists",
                    "path": "variables/Bx/attributes/LABLAXIS",
                    "message": "{% if valid %}LABLAXIS present{% else %}missing{% endif %}",
                },
                {
                    "check": "exists",
                    "path": "variables/Bx/attributes/UNITS",
                    "message": "{% if valid %}UNITS present{% else %}missing{% endif %}",
                },
            ],
        }
    )
    result = assertion.evaluate(_file_with_var({"LABLAXIS": "B", "UNITS": "nT"}), Severity.ERROR)
    assert result.valid
    messages = _leaf_messages(result)
    assert "LABLAXIS present" in messages
    assert "UNITS present" in messages
    assert "All assertions in 'all_of' passed successfully." not in messages
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_passing_rule_clarity.py::test_all_of_pass_preserves_each_member -v`
Expected: FAIL (today the only message is the generic "all_of passed" string).

- [ ] **Step 3: Update `AllOf.evaluate` success path**

Change the method's return-type annotation to the union and replace the trailing success `return` (the one after the `for` loop) with a group of the collected sub-results. The full method becomes:

```python
class AllOf(BaseAssertionGroup):
    model_config = ConfigDict(frozen=True)
    check: Literal["all_of"] = "all_of"  # type: ignore[assignment]

    def evaluate(self, file: File, severity: Severity) -> ValidationResult | ValidationResultGroup:
        results: list[ValidationResult | ValidationResultGroup] = []
        for assertion in self.assertions:
            result = assertion.evaluate(file, severity)
            if not result.valid:
                detail = _first_failure(result)
                message, target = detail if detail else ("Assertion failed in 'all_of'", "")
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=severity,
                    message=self._result_message(False, message),
                    target=target,
                )
            results.append(result)
        # Pass path: preserve each member's result so the report can show which
        # value/member was validated (an internal wrapper group the reporter flattens).
        return ValidationResultGroup(
            name="all_of", rule_reference="", results=results, severity=severity
        )
```

Note: the `name="all_of"` group has no `rule_reference`/`message`/`url`, so the reporter's `is_internal_wrapper` flattens it away (Task 4).

- [ ] **Step 4: Run the test and the guard**

Run: `uv run pytest tests/test_passing_rule_clarity.py tests/test_failing_leaf_invariance.py -v`
Expected: PASS (members preserved; guard green — failure path unchanged).

- [ ] **Step 5: Run the resolver + suite tests as a second safety net**

Run: `uv run pytest tests/test_resolver_loop.py tests/test_resolver_engine.py tests/test_cdf_istp.py -q`
Expected: PASS. (If a count/structure assertion fails here, it is an intended pass-path count change — note it; the failing-leaf guard proves failures are intact.)

- [ ] **Step 6: Commit**

```bash
git add src/astralint/base/yaml_rules/assertions/combinations.py tests/test_passing_rule_clarity.py
git commit -m "feat(engine): all_of preserves passing member results

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Shared `reports/_findings.py` presentation helper

One place defines: which groups are internal wrappers, how the nearest rule reference is stamped onto leaves, and which leaves are pass-path noise. Both reporters call it.

**Files:**
- Create: `src/astralint/reports/_findings.py`
- Test: `tests/test_passing_rule_clarity.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_passing_rule_clarity.py`:

```python
from astralint.reports._findings import display_children, is_internal_wrapper


def test_display_children_flattens_stamps_reference_and_drops_noise():
    skipped = ValidationResult(
        valid=True, reference="", severity=Severity.SKIPPED,
        message="Condition not met, assertion skipped.", target="",
    )
    not_required = ValidationResult(
        valid=True, reference="", severity=Severity.INFO,
        message="DOI did not match any values (not required)", target="DOI",
    )
    real = ValidationResult(
        valid=True, reference="", severity=Severity.ERROR,
        message="Data_type is valid", target="Data_type", value="L2>level 2",
    )
    wrapper = ValidationResultGroup(
        name="Matches", rule_reference="", severity=Severity.ERROR,
        results=[real, skipped, not_required],
    )
    rule = ValidationResultGroup(
        name="DataTypeFormat", rule_reference="ISTP-GA-006", severity=Severity.ERROR,
        results=[wrapper], url="http://example/doc",
    )
    children = display_children(rule)
    assert all(isinstance(c, ValidationResult) for c in children)
    assert [c.message for c in children] == ["Data_type is valid"]
    assert children[0].reference == "ISTP-GA-006"  # stamped from the rule group


def test_is_internal_wrapper():
    assert is_internal_wrapper(
        ValidationResultGroup(name="all_of", rule_reference="", severity=Severity.ERROR, results=[])
    )
    assert not is_internal_wrapper(
        ValidationResultGroup(
            name="r", rule_reference="ISTP-GA-006", severity=Severity.ERROR, results=[]
        )
    )
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_passing_rule_clarity.py::test_display_children_flattens_stamps_reference_and_drops_noise -v`
Expected: FAIL with `ModuleNotFoundError: astralint.reports._findings`.

- [ ] **Step 3: Create the helper**

```python
# src/astralint/reports/_findings.py
"""Shared presentation logic for the console and HTML reporters.

Turns a rule's raw result tree into the flat list of *display* items: internal
per-assertion wrapper groups are flattened away, each leaf is stamped with the
nearest enclosing rule reference, and pass-path noise leaves (skipped conditions,
optional-absent attributes) are dropped. Real groupings — rule groups and
per-file/suite groups — are preserved so the renderers keep their structure.
"""

from ..base import Severity, ValidationResult, ValidationResultGroup

# Mirrors the valid branch of `_NO_MATCH_TEMPLATE` in
# base/yaml_rules/assertions/base.py and compare_to.py. These leaves mean
# "the optional attribute is absent", not "a member is valid".
_NOT_REQUIRED_MARKER = "did not match any values (not required)"


def is_internal_wrapper(group: ValidationResultGroup) -> bool:
    """A per-assertion ``…Assertion``/``all_of``/``IfThen`` wrapper, as opposed to a
    rule group (has a ``rule_reference``) or a per-file/suite group (has a ``message``
    and/or ``url``). Only wrappers are flattened away."""
    return not group.rule_reference and not group.message and not group.url


def _is_pass_noise(leaf: ValidationResult) -> bool:
    """A passing leaf that carries no information about a validated member."""
    if leaf.severity == Severity.SKIPPED:
        return True
    return leaf.valid and _NOT_REQUIRED_MARKER in leaf.message


def display_children(
    group: ValidationResultGroup, reference: str = ""
) -> list[ValidationResult | ValidationResultGroup]:
    """Items to render directly under ``group``: wrappers flattened, leaves stamped
    with the nearest rule reference, pass-path noise dropped. Non-wrapper subgroups
    are returned as-is for the renderer to recurse into."""
    reference = group.rule_reference or reference
    items: list[ValidationResult | ValidationResultGroup] = []
    for child in group.results:
        if isinstance(child, ValidationResultGroup):
            if is_internal_wrapper(child):
                items.extend(display_children(child, reference))
            else:
                items.append(child)
        elif not _is_pass_noise(child):
            items.append(
                child if child.reference else child.model_copy(update={"reference": reference})
            )
    return items
```

- [ ] **Step 4: Run the tests to verify pass**

Run: `uv run pytest tests/test_passing_rule_clarity.py -k "display_children or is_internal_wrapper" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/astralint/reports/_findings.py tests/test_passing_rule_clarity.py
git commit -m "feat(reports): shared rule-findings helper (flatten, stamp ref, drop noise)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: HTML reporter uses the shared helper

Replace `html.py`'s local `_is_internal_wrapper`/`_display_children` with the shared helper so noise is dropped and references are stamped. `RESULT_TEMPLATE` already renders `result.reference`, so stamped leaves now show their rule code.

**Files:**
- Modify: `src/astralint/reports/html.py`
- Test: `tests/test_passing_rule_clarity.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_passing_rule_clarity.py`:

```python
from astralint.reports.html import generate_html_fragment


def _passing_rule_tree() -> ValidationResultGroup:
    real = ValidationResult(
        valid=True, reference="", severity=Severity.ERROR,
        message="Data_type is valid", target="Data_type", value="L2>level 2",
    )
    not_required = ValidationResult(
        valid=True, reference="", severity=Severity.INFO,
        message="DOI did not match any values (not required)", target="DOI",
    )
    wrapper = ValidationResultGroup(
        name="Matches", rule_reference="", severity=Severity.ERROR,
        results=[real, not_required],
    )
    return ValidationResultGroup(
        name="DataTypeFormat", rule_reference="ISTP-GA-006", severity=Severity.ERROR,
        results=[wrapper],
    )


def test_html_passing_rule_shows_reference_and_drops_not_required():
    html = generate_html_fragment(_passing_rule_tree())
    assert "ISTP-GA-006" in html
    assert "Data_type is valid" in html
    assert "not required" not in html
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_passing_rule_clarity.py::test_html_passing_rule_shows_reference_and_drops_not_required -v`
Expected: FAIL (`"not required"` still present; reference absent on the leaf).

- [ ] **Step 3: Rewire `html.py` to the shared helper**

In `src/astralint/reports/html.py`:

1. Add the import near the top (after the existing `from ..base import ...`):

```python
from ._findings import display_children
```

2. Delete the local `_is_internal_wrapper` function and the local `_display_children` function (lines defining them).

3. In `_render_item`, change the `children=_display_children(item)` argument to `children=display_children(item)`.

- [ ] **Step 4: Run the new test + the existing HTML tests**

Run: `uv run pytest tests/test_passing_rule_clarity.py tests/test_html_readability.py tests/test_reports.py -v`
Expected: the new test PASSES. If `test_html_readability.py` asserts the old `_display_children` symbol or a now-dropped "not required" line or a leaf count, update that assertion to the new behavior (intended change) and re-run.

- [ ] **Step 5: Commit**

```bash
git add src/astralint/reports/html.py tests/test_passing_rule_clarity.py tests/test_html_readability.py
git commit -m "feat(reports): HTML uses shared findings helper (stamp ref, drop noise)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

(Only include `tests/test_html_readability.py` in the commit if you changed it.)

---

## Task 6: Console `--show-passed` tree uses the shared helper

The console tree (`_render_group`) currently recurses over raw `group.results`, showing wrapper layers (`IfThen []`) and empty-reference leaves (`✔ :`). Route it through `display_children` and render the stamped reference on each leaf.

**Files:**
- Modify: `src/astralint/reports/console.py`
- Test: `tests/test_passing_rule_clarity.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_passing_rule_clarity.py`:

```python
from rich.console import Console
from astralint.reports.console import console_report


def _render_to_text(tree: ValidationResultGroup) -> str:
    console = Console(width=200, record=True, color_system=None)
    console_report(tree, console)
    return console.export_text()


def test_console_show_passed_stamps_reference_and_drops_noise():
    out = _render_to_text(_passing_rule_tree())
    assert "ISTP-GA-006" in out
    assert "Data_type is valid" in out
    assert "not required" not in out
    assert "✔ :" not in out  # no empty-reference leaf
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_passing_rule_clarity.py::test_console_show_passed_stamps_reference_and_drops_noise -v`
Expected: FAIL (`"not required"` present and/or `"✔ :"` present).

- [ ] **Step 3: Update `console.py`**

1. Add the import after the existing `from ..base import ...`:

```python
from ._findings import display_children
```

2. Update `_render_result` so a leaf with a reference shows it and one without still reads cleanly. Replace the `text = Text.from_markup(...)` line with:

```python
    label = f"{res.reference}: " if res.reference else ""
    text = Text.from_markup(f"{icon} [bold]{label}[/]{escape(res.message)}")
```

3. In `_render_group`, replace the child loop `for item in group.results:` with the shared helper:

```python
    for item in display_children(group):
        tree.add(_render(item))
```

- [ ] **Step 4: Run the new test + console tests**

Run: `uv run pytest tests/test_passing_rule_clarity.py tests/test_console_summary.py tests/test_report_ergonomics.py tests/test_filters.py -v`
Expected: the new test PASSES. Update any assertion in the console tests that relied on a wrapper layer, an empty-reference leaf, or a now-dropped "not required" line (intended change).

- [ ] **Step 5: Commit**

```bash
git add src/astralint/reports/console.py tests/test_passing_rule_clarity.py
git commit -m "feat(reports): console --show-passed stamps ref, flattens wrappers, drops noise

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

(Add any console test files you had to update to the commit.)

---

## Task 7: Full verification + visual preview

**Files:** none (verification only) — plus possibly small test-count fixes surfaced here.

- [ ] **Step 1: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS. If any failures remain, they should be only count/structure assertions reflecting the intended `all_of` expansion — fix each by updating the expected count to the new (correct) value, and confirm the failing-leaf guard (`tests/test_failing_leaf_invariance.py`) is still green. Do NOT change behavior to satisfy a stale count.

- [ ] **Step 2: Lint**

Run: `make lint`
Expected: clean (codespell → ruff check → ruff format → basedpyright). Fix anything reported.

- [ ] **Step 3: Generate a console `--show-passed` capture on a real CDF**

Run:

```bash
uv run astralint lint tests/resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf --suite ISTP --show-passed | head -60
```

Expected: passing rules show `✔ <REFERENCE>  <target> › <message>` lines with no `✔ :`, no `IfThen []` wrapper layer, and no "(not required)" lines.

- [ ] **Step 4: Generate an HTML preview screenshot for visual judgement**

Generate the HTML (throwaway file, never committed — it is already untracked):

```bash
uv run python -c "
from astralint.base import get_suite, load_file
from astralint.reports.html import generate_html
html = generate_html(get_suite('ISTP').run(load_file('tests/resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf')))
open('report-preview.html','w').write(html)
print('wrote report-preview.html')
"
```

Then screenshot it (per the project technique):

```bash
uv run --with playwright python -m playwright install chromium >/dev/null 2>&1
uv run --with playwright python -c "
from playwright.sync_api import sync_playwright
import pathlib
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(color_scheme='dark')
    pg.goto('file://' + str(pathlib.Path('report-preview.html').resolve()))
    pg.screenshot(path='report-preview.png', full_page=True)
    b.close()
print('wrote report-preview.png')
"
```

Read `report-preview.png` and present both the console capture and the screenshot to the user for the deferred "(not required)" judgement. Do NOT commit `report-preview.html`/`report-preview.png` (throwaways).

- [ ] **Step 5: Final guard re-run**

Run: `uv run pytest tests/test_failing_leaf_invariance.py tests/test_resolver_loop.py -q`
Expected: PASS — confirms the resolver/failure contract held through every change.

---

## Self-review notes

- **Spec coverage:** §1 engine (Tasks 2–3), §2 shared reporting helper (Task 4) + both surfaces (Tasks 5–6), §3 safety (Task 1 guard + Task 3 step 5 + Task 7 step 5). Testing list items 1–5 map to Tasks 4/5/6 (display behavior), Task 3 (combinator), Task 1 (guard), Task 3 step 5 (resolver). Open sub-decision surfaced for the user in Task 7 step 4.
- **No placeholders:** every code step shows full code; `EXPECTED` in Task 1 is filled by the printed Step-1 baseline before the test is committed.
- **Type consistency:** `display_children`/`is_internal_wrapper` (Task 4) are the exact names imported in Tasks 5–6; `_first_pass` (Task 2) is reused conceptually but each task defines what it needs; `AllOf` returns `ValidationResult | ValidationResultGroup` consistently with how `IfThen` already returns the union.
