# Readable passing rules — design

**Date:** 2026-06-21
**Status:** approved (pending spec review)
**Branch:** `feat/readable-passing-rules`

## Problem

When passing rules are shown — the HTML report (always) and the console tree under
`--show-passed` — the output is uninformative noise. A reader cannot tell *which rule*
passed or *what value/member* was validated. Two concrete examples reported by the user:

Console (`--show-passed`):

```
── IfThen []
   └── ✔ : All assertions in 'all_of' passed successfully.
```

HTML:

```
✓ Project did not match any values (not required) @ Project
✓ All assertions in 'all_of' passed successfully.
```

These lines carry no rule reference (`✔ :`), no concrete subject, and the generic
combinator text ("all_of passed") says nothing about which member was checked.

## Root cause

A rule evaluates to a `ValidationResultGroup` (name = rule name, `rule_reference` = the
rule code, `url` = doc link), whose children are one result per top-level assertion.

There are two failure modes in the current output:

1. **Simple rules** (the majority, e.g. `DataTypeFormat`, `CatdescLength`): their leaves
   already carry the concrete `target` and `value` (set in `BaseAssertion.evaluate`).
   They only *render* badly because
   - the leaf's `reference` is empty, so the console/HTML show `✔ :` with no rule code, and
   - the console does not flatten the internal per-assertion wrapper groups
     (`Matches`, `NotEmpty`, …); HTML already flattens them via `_is_internal_wrapper`.

2. **Combinator rules** (7 rules using `if_then` / `all_of` / `any_of`, e.g.
   `DataVariableAttributes`): on success, `AllOf` and `AnyOf` **discard their children**
   and emit a single generic leaf ("All assertions in 'all_of' passed successfully") with
   no reference, target, or value. The per-member detail is destroyed in the engine, so no
   reporter can recover it.

Additionally, optional-absent attributes produce an `INFO` "… did not match any values
(not required)" leaf and unmet conditions produce a `SKIPPED` "Condition not met,
assertion skipped." leaf. Neither represents "a member that is valid"; both are pure noise
on the pass path.

## Goal

For a passing rule, show its header (name + `[REFERENCE]` + 📖 docs) followed by **one
self-describing line per validated member**, each line carrying the rule reference, the
concrete variable/attribute, and (where scalar) the value — and nothing else. Reducing
noise further remains the job of the existing controls: omit `--show-passed` in the
console; use the "show only failed" toggle in HTML.

Non-goal: changing any failing-path output. The resolver routes on failing-leaf
`(reference, target, message)`; those must stay byte-identical.

## Design

### 1. Engine — stop discarding passing members (pass path only)

In `base/yaml_rules/assertions/combinations.py`, on the **success path only**:

- **`AllOf`** → return a `ValidationResultGroup` of its sub-results instead of one generic
  summary leaf (mirrors what `IfThen` already does today). This lets
  "Bx_gse has all required data attributes" survive to the report.
- **`AnyOf`** → return the **passing** sub-result (the member that actually satisfied it),
  not a generic "at least one passed" leaf. (Implementation note: `AnyOf` already returns
  early on the first passing `result`; return that `result` itself instead of a synthesized
  summary leaf.)
- **`OneOf` / `AtLeast` / `AtMost` / `Exactly`** → unchanged: keep their single summary
  leaf, because their meaning *is* the count ("exactly 1 passed"). They get a reference
  stamped at render time like every other leaf.
- **`IfThen` / `IfThenElse`** → unchanged: already preserve children.

The **failure paths of every combinator are unchanged**, including `AllOf`'s
first-failure target/message and `AnyOf`'s same-target propagation that the resolver
depends on.

Consequence: passing combinator subtrees now contain N leaves where they previously
contained 1. This is intentional and more accurate.

### 2. Reporting — one shared "rule findings" transform

Factor the presentation logic currently split between `reports/console.py`
(`_collect_findings`) and `reports/html.py` (`_display_children` / `_is_internal_wrapper`)
into a single shared helper that both surfaces call, so the two cannot drift. Given a node,
it yields the flat list of *display leaves* by:

- **Flattening internal wrapper groups** — a group with no `rule_reference`, no `message`,
  and no `url` (the existing `_is_internal_wrapper` predicate). This preserves real rule
  groups and per-file/suite groups. The console does not do this today; this brings it to
  parity with HTML.
- **Stamping the nearest enclosing rule reference** onto each leaf, so a leaf never renders
  as `✔ :` — it renders as `✔ ISTP-VA-002`. (Console's `_collect_findings` already carries
  the nearest reference down; this generalizes it and applies it to the tree renderers, not
  just the quiet view.)
- **Dropping pure-noise leaves on the pass path**: `SKIPPED` "Condition not met" leaves and
  the `INFO` "… did not match any values (not required)" leaves. These mean "nothing to
  check here", not "a valid member".
- Preserving the `target` and `value` the real assertion leaves already carry.

Rendered result, per passing rule:

Console (`--show-passed`):

```
DataVariableAttributes  [ISTP-VA-002]  📖 docs
  ✔ ISTP-VA-002  Bx_gse › Bx_gse has all required data attributes
  ✔ ISTP-VA-002  Bx_gse › LABLAXIS present
```

HTML (collapsible group; "show only failed" hides it):

```
✓ ISTP-VA-002  Bx_gse › Bx_gse has all required data attributes   @ Bx_gse
```

The shared helper lives in one module (e.g. a small function in `reports/__init__.py` or a
new `reports/_findings.py`) and is imported by both reporters. Each reporter keeps its own
rendering (rich `Tree` vs HTML groups); only the *what to show under a rule* logic is
shared.

### 3. Safety — what counts leaves, and how it stays correct

- **Fail paths byte-identical.** A regression guard hashes the set of *failing* leaves
  `(reference, target, severity, message)` across the real resource CDFs and asserts this
  change does not alter it. This pins the resolver/convergence contract. The existing
  resolver convergence tests are a second guard.
- **Resolver and `failures_only()`** walk only failing leaves, so they are untouched once
  the above holds.
- **Counts shift on the pass path, by design.** `_count_stats` (HTML stat cards) and
  `count_by_severity` (console verdict's INFO count) count leaves; an `all_of` that was 1
  "passed" leaf becomes N. This is more accurate but is a visible number change; tests that
  assert old counts are updated as intended changes, not silently. The verdict's
  error/warning counts do not move (no failures on the pass path).
- **Tests asserting the old generic strings** ("All assertions in 'all_of' passed
  successfully", etc.) are updated, since removing that text is the point.

## Testing

TDD, reproducer-first:

1. A simple rule (e.g. `DataTypeFormat`) passing → its display leaves carry the rule
   reference, the concrete target, and the value; no `Matches`/`NotEmpty` wrapper layer; no
   empty-reference leaf.
2. A combinator rule (e.g. `DataVariableAttributes`) passing on a real variable → member
   detail survives (one leaf per checked member with its message), no generic
   "all_of passed" leaf.
3. The "(not required)" `INFO` leaf and the `SKIPPED` "condition not met" leaf are absent
   from the passing display output.
4. **Failing-leaf hash guard**: the set of failing leaves over the resource CDFs is
   unchanged by this work.
5. Existing resolver convergence tests stay green.

Final verification: full `pytest` + `make lint` green; generate an actual HTML preview
(playwright screenshot technique) and a console `--show-passed` capture on a real CDF for
visual judgement, including the "(not required)" drop.

## Open sub-decision (defer to visual output)

Dropping the "(not required)" `INFO` leaves also removes them from the console verdict's
INFO count. The user will judge on the rendered output whether to drop them entirely or
keep them counted-but-unlisted.
