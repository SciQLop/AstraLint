# Advanced rule selection (web demo) — design

**Date:** 2026-06-22
**Status:** approved (pending spec review)
**Branch:** `feat/advanced-rule-selection` (stacked on `feat/report-default-failed`)

## Problem

The web demo (`docs/demo/index.html`) runs a fixed conformance suite over the uploaded
file with no way to turn individual rules off. Users evaluating their files often want to
silence rules that don't apply to their dataset (e.g. CDAWeb-ingestion rules for a file
never destined for CDAWeb) and see the result immediately. The validation engine already
supports this — `ConformanceSuite.run(file, ignore=[...])` drops rules whose `reference` or
`name` regex-matches an entry (`filter_rules` / `_matches_any_pattern`) — but the demo never
passes `ignore`.

## Goal

An "Advanced" panel in the demo, collapsed by default, listing every rule of the currently
selected suite with a checkbox in front of each. Unchecking a rule disables it: the analysis
re-runs immediately (reusing the existing suite-change re-run hook) with that rule excluded
from **both** the validation report and the auto-fix preview/apply. The panel repopulates
(all enabled) whenever the suite changes.

Non-goals (v1): persisting the ignore set to project config, a shareable `&ignore=` URL,
free-text/regex entry, and wiring the CLI `fix` command's config `ignore` into `converge`.
The canonical place to persist rule selection remains `.astralint.yaml` / `pyproject.toml`;
the web panel is session-only.

## Design

### 1. Engine — thread `ignore` through `converge`

`resolver/loop.py`: add `ignore: list[str] | None = None` to `converge(cdf_bytes, suite, ...,
ignore=None)` and pass it to the internal `suite.run(file, ignore=ignore)` call. Default
`None` is byte-identical to today, so existing converge/resolver behavior is unchanged. This
is the single in-package change; it lets a disabled rule disappear from the fix proposals and
the applied fixes, not only the report.

The validation report side needs no engine change — `suite.run(file, ignore=...)` already
exists.

Ignore values are **rule references** (e.g. `ISTP-GA-016`), taken verbatim from the
checklist; `filter_rules` regex-full-matches them against each rule's `reference` or `name`,
so exact codes match with no globbing.

### 2. Demo Python (inline in `index.html`)

- **`list_rules(suite_name) -> str`** — returns JSON `[{"reference", "name", "description",
  "severity"}, …]` by iterating `get_suite(suite_name).rules`. Used to populate the panel.
  Returns `[]`-with-error JSON shape consistent with the other demo functions if the suite is
  unknown.
- **`validate_file_bytes(data, filename, suite_name, ignore_json="[]")`** and
  **`validate_file_url(url, suite_name, ignore_json="[]")`** — parse `ignore_json` (a JSON
  array of references) and call `suite.run(file, ignore=ignore or None)`.
- **`fix_file_bytes` / `fix_file_url` / `_converge_to_json`** — gain the same `ignore_json`
  and pass `ignore=` into `converge`.

`ignore_json` is a JSON string for a clean JS↔Pyodide boundary (matching how the fix path
already passes scalars via `pyodide.globals.set`).

### 3. Demo UI & wiring

A collapsible **"Advanced — rule selection"** panel directly under the suite selector,
collapsed by default:

```
( ISTP ) ( CDAWeb ) ( PDS4 ) ( SOLARNET )

▸ Advanced — rule selection (42 of 42 enabled)
  [Enable all] [Disable all]
  ☑ ISTP-GA-001  MandatoryGlobalAttributes   ERROR
  ☑ ISTP-GA-016  CDAWebRequired…             WARNING
  ☑ ISTP-VA-019  FillvalOutsideRange         ERROR
  … scrollable …   (rule description on hover)
```

- **Source of truth = the checkboxes.** `currentIgnore()` returns the `reference`s of all
  *unchecked* rows as an array; it is passed (JSON-encoded) to `validate_*` and `fix_*`.
- **`populateRuleList(suiteName)`** awaits Pyodide `list_rules`, renders one row per rule
  (checkbox checked, label `reference — name`, severity chip reusing the existing `.severity`
  classes, `title=description`), and updates the "(N of M enabled)" count. Called once when
  Pyodide becomes ready (initial ISTP) and on every suite change.
- **Wiring (reusing `revalidateCurrent` from `feat/report-default-failed`):**
  - *Suite change* → `await populateRuleList(suite)` (resets to all-enabled) →
    `revalidateCurrent()`.
  - *Checkbox toggle* — one delegated `change` listener on the list container → update the
    count → `revalidateCurrent()` (a no-op until a file is loaded).
  - *Enable all / Disable all* — set all checkboxes, update count, `revalidateCurrent()`.
  - `validateBytes`, `processFileFromUrl`, and `fixAndDownload` each read `currentIgnore()`
    and pass it through to their Pyodide call.
- **States/edges:** until Pyodide is ready the panel shows "loading rules…"; the panel is
  visible (collapsed) regardless of whether a file is loaded; stub suites (PDS4/SOLARNET, 1
  rule) render normally; disabling every rule yields an empty report (acceptable — the user
  did it).

Styling matches the existing demo: the collapse mirrors the report-group pattern, the
severity chip reuses `.severity.ERROR/.WARNING/.INFO`.

## Components & boundaries

- `converge(..., ignore=None)` — pure engine, testable in isolation; the only package change.
- `list_rules` — a thin JSON projection of `get_suite(name).rules`; demo-local.
- `validate_*` / `fix_*` — demo-local; only addition is the parsed `ignore` argument.
- `populateRuleList` / `currentIgnore` / the panel — demo-local JS; the panel's DOM is the
  single source of truth for the ignore set (no parallel JS state to drift).

## Testing

- **Engine (pytest, in-package):** on the MMS resource CDF,
  `converge(bytes, suite, ignore=["ISTP-VA-019"])` yields a converged report with no
  `ISTP-VA-019` finding, while default `converge(...)` still surfaces it; and `ignore=None`
  leaves existing converge behavior unchanged.
- **Demo JS wiring (Playwright, no network, stub technique):** stub `pyodide` / `list_rules`
  / `validate_*`; assert `populateRuleList` renders one checked checkbox per rule; unchecking
  rows makes `currentIgnore()` return exactly those references; a checkbox toggle invokes the
  stubbed validate with that ignore array; a suite change repopulates and resets to
  all-enabled. Plus the JS parse / no-uncaught-error load check.
- **Manual / browser:** the inline `list_rules` and the true Pyodide end-to-end can't run
  headless without network, so serve the demo locally for the user to eyeball the panel and a
  real disable→re-run cycle.

## Branch / delivery

Stacked on `feat/report-default-failed` (it reuses that branch's `revalidateCurrent` hook).
Rebase onto `main` once `feat/report-default-failed` merges; ship as its own PR off the
`jeandet` fork into `SciQLop/AstraLint`.
