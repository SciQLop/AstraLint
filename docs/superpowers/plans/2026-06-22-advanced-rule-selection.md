# Advanced Rule Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a collapsible "Advanced — rule selection" panel to the web demo that lists every rule of the selected suite with a checkbox; unchecking a rule disables it and re-runs the analysis (report + auto-fix) with that rule excluded.

**Architecture:** One small backward-compatible engine change (thread `ignore` through `converge`), then demo-local Python (`list_rules` + an `ignore_json` arg on the validate/fix functions) and demo-local JS (the panel, `populateRuleList`/`currentIgnore`, and wiring that reuses the existing `revalidateCurrent` re-run hook). The checkboxes' DOM is the single source of truth for the ignore set.

**Tech Stack:** Python 3.11+ (Pydantic, the AstraLint engine), Pyodide (in-browser Python), vanilla JS + HTML/CSS in `docs/demo/index.html`, pytest, Playwright (for ad-hoc JS verification only — not a collected test).

**Spec:** `docs/superpowers/specs/2026-06-22-advanced-rule-selection-design.md`

**Branch:** Work on `feat/advanced-rule-selection` (already created, stacked on `feat/report-default-failed` whose `revalidateCurrent` hook this reuses). Do NOT switch branches.

**Conventions:** Never `git add -A`/`.` (the tree carries untracked throwaways: `report-preview.*`, `test.html`, `.gitignore.back`, `uv.lock`) — stage named files only. Commit messages end with the repo's Co-Authored-By trailer. The demo's Python lives inline inside a `pyodide.runPythonAsync(\`…\`)` template string in `docs/demo/index.html`; the demo's JS lives in `<script>` blocks in the same file. Only `converge` (in `src/`) is unit-testable; the demo changes are verified by an ad-hoc Playwright script and by serving the demo for the user.

---

## File Structure

- `src/astralint/resolver/loop.py` — **modify**. `converge` gains an `ignore` param passed to both internal `suite.run` calls.
- `tests/test_resolver_loop.py` — **modify**. Two tests for the `ignore` param (this file already has the `_CDF` path and converge imports).
- `docs/demo/index.html` — **modify**. Inline Python (`list_rules` + `ignore_json` on validate/fix funcs); the Advanced panel markup + CSS; JS (`populateRuleList`, `currentIgnore`, `updateRuleCount`, `setAllRules`, wiring, and threading `ignore` into the validate/fix calls).

---

## Task 1: Engine — thread `ignore` through `converge`

**Files:**
- Modify: `src/astralint/resolver/loop.py`
- Test: `tests/test_resolver_loop.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_resolver_loop.py` (the module already defines `_CDF` and imports `converge`, `get_suite`):

```python
def test_converge_ignore_all_rules_converges_immediately():
    """ignore reaches suite.run inside converge: dropping every ISTP rule leaves
    nothing to validate, so the file 'converges' with no fixes applied."""
    suite = get_suite("ISTP")
    assert suite is not None
    with open(_CDF, "rb") as fh:
        data = fh.read()
    report, _ = converge(data, suite, ignore=["ISTP-.*"])
    assert report.converged is True
    assert report.applied == []
    assert report.remaining_errors == 0


def test_converge_ignore_none_matches_default():
    """ignore=None is byte-identical to omitting it (backward compatibility)."""
    suite = get_suite("ISTP")
    assert suite is not None
    with open(_CDF, "rb") as fh:
        data = fh.read()
    default, _ = converge(data, suite)
    explicit_none, _ = converge(data, suite, ignore=None)
    assert (len(default.applied), default.remaining_errors, default.converged) == (
        len(explicit_none.applied),
        explicit_none.remaining_errors,
        explicit_none.converged,
    )
```

- [ ] **Step 2: Run to verify the new test fails**

Run: `uv run pytest tests/test_resolver_loop.py::test_converge_ignore_all_rules_converges_immediately -v`
Expected: FAIL with `TypeError: converge() got an unexpected keyword argument 'ignore'`.

- [ ] **Step 3: Add the `ignore` param and thread it into both `suite.run` calls**

In `src/astralint/resolver/loop.py`, change the `converge` signature:

```python
def converge(
    cdf_bytes: bytes,
    suite: ConformanceSuite,
    max_iter: int = 10,
    filename: str | None = None,
    ignore: list[str] | None = None,
) -> tuple[ConvergenceReport, bytes]:
```

Change the in-loop run (currently `results = suite.run(file)`):

```python
        results = suite.run(file, ignore=ignore)
```

Change the final run (currently `final = suite.run(final_file)`):

```python
    final = suite.run(final_file, ignore=ignore)
```

Leave everything else unchanged.

- [ ] **Step 4: Run both new tests + the existing loop tests**

Run: `uv run pytest tests/test_resolver_loop.py -v`
Expected: PASS (the two new tests pass; the pre-existing converge tests still pass — `ignore` defaults to `None`).

- [ ] **Step 5: Commit**

```bash
git add src/astralint/resolver/loop.py tests/test_resolver_loop.py
git commit -m "feat(resolver): thread an ignore list through converge

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Demo Python — `list_rules` + `ignore_json` on validate/fix functions

**Files:**
- Modify: `docs/demo/index.html` (the inline Python inside the `pyodide.runPythonAsync(\`…\`)` block that begins `from astralint.base import get_suite, list_all_suites`)

No pytest (demo-inline Python). Verified later in Task 5.

- [ ] **Step 1: Add `list_rules`**

Insert this function immediately after the `astralint_version()` function (right before `def _converge_to_json`):

```python
def list_rules(suite_name: str = "ISTP") -> str:
    """JSON list of the suite's rules, for the advanced rule-selection panel."""
    import json
    suite = get_suite(suite_name)
    if suite is None:
        return json.dumps({"error": f'Suite "{suite_name}" not found'})
    return json.dumps([
        {"reference": r.reference, "name": r.name,
         "description": r.description, "severity": r.severity.value}
        for r in suite.rules
    ])
```

- [ ] **Step 2: Thread `ignore_json` into `_converge_to_json` and the fix entry points**

Replace the `_converge_to_json` signature and its `converge(...)` call. Change:

```python
def _converge_to_json(data: bytes, filename: str, suite_name: str) -> str:
```
to:
```python
def _converge_to_json(data: bytes, filename: str, suite_name: str, ignore_json: str = "[]") -> str:
```

Inside it, change:
```python
        report, fixed = converge(bytes(data), suite, filename=filename)
```
to (note: `_converge_to_json` already does `import json` at its top, so reuse it):
```python
        ignore = json.loads(ignore_json) or None
        report, fixed = converge(bytes(data), suite, filename=filename, ignore=ignore)
```

Change the two fix entry points:
```python
def fix_file_bytes(data: bytes, filename: str, suite_name: str = "ISTP") -> str:
    return _converge_to_json(data, filename, suite_name)

def fix_file_url(url: str, suite_name: str = "ISTP") -> str:
    from astralint.base.codec import get_remote_file
    filename = url.rstrip("/").split("/")[-1] or "file.cdf"
    return _converge_to_json(get_remote_file(url), filename, suite_name)
```
to:
```python
def fix_file_bytes(data: bytes, filename: str, suite_name: str = "ISTP", ignore_json: str = "[]") -> str:
    return _converge_to_json(data, filename, suite_name, ignore_json)

def fix_file_url(url: str, suite_name: str = "ISTP", ignore_json: str = "[]") -> str:
    from astralint.base.codec import get_remote_file
    filename = url.rstrip("/").split("/")[-1] or "file.cdf"
    return _converge_to_json(get_remote_file(url), filename, suite_name, ignore_json)
```

- [ ] **Step 3: Thread `ignore_json` into the two validate functions**

Change:
```python
def validate_file_bytes(data: bytes, filename: str, suite_name: str = "ISTP") -> str:
```
to:
```python
def validate_file_bytes(data: bytes, filename: str, suite_name: str = "ISTP", ignore_json: str = "[]") -> str:
```
and inside it change `results = suite.run(file)` to:
```python
        import json
        results = suite.run(file, ignore=json.loads(ignore_json) or None)
```

Change:
```python
def validate_file_url(url: str, suite_name: str = "ISTP") -> str:
```
to:
```python
def validate_file_url(url: str, suite_name: str = "ISTP", ignore_json: str = "[]") -> str:
```
and inside it change `results = suite.run(file)` to:
```python
        import json
        results = suite.run(file, ignore=json.loads(ignore_json) or None)
```

(`_fix_preview(file, results)` needs no change: it already receives the filtered `results`, so ignored rules' fixes are excluded from the preview automatically.)

- [ ] **Step 4: Sanity check that the Python block still parses**

Run: `uv run python -c "import ast, re, pathlib; html=pathlib.Path('docs/demo/index.html').read_text(); m=re.search(r'from astralint.base import get_suite.*?(?=\\\\n                \`\\\\))', html, re.S); ast.parse(m.group(0)); print('python block parses')"`
Expected: prints `python block parses` (if the regex fails to capture, instead copy the inline Python between the backticks into a scratch file and run `uv run python -m py_compile` on it — the goal is only to confirm valid Python syntax).

- [ ] **Step 5: Commit**

```bash
git add docs/demo/index.html
git commit -m "feat(demo): list_rules + ignore_json on validate/fix Python entry points

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Demo UI — the Advanced panel (markup, CSS, populate/state helpers)

**Files:**
- Modify: `docs/demo/index.html` (HTML markup after the suite selector; CSS in the `<style>` block; JS helpers in the main `<script>`)

- [ ] **Step 1: Add the panel markup after the suite selector**

Find the closing `</div>` of the suite-select block (the `<div class="suite-select">…</div>` that ends right before `<div class="upload-zone" id="upload-zone">`). Insert immediately after that closing `</div>` and before the `<div class="upload-zone"…>`:

```html
            <details class="advanced-rules" id="advanced-rules">
                <summary>Advanced — rule selection <span id="rule-select-count" class="rule-count"></span></summary>
                <div class="rule-actions">
                    <button type="button" id="rules-enable-all" class="rule-action">Enable all</button>
                    <button type="button" id="rules-disable-all" class="rule-action">Disable all</button>
                </div>
                <div id="rule-list" class="rule-list"><div class="rule-loading">loading rules…</div></div>
            </details>
```

- [ ] **Step 2: Add CSS for the panel**

Add this near the other component styles in the `<style>` block (e.g. right after the `.suite-select` rules):

```css
        .advanced-rules {
            margin: 1rem 0 1.5rem;
            border: 1px solid var(--color-border, #e2e8f0);
            border-radius: 8px;
            padding: 0.5rem 1rem;
        }
        .advanced-rules > summary {
            cursor: pointer;
            font-weight: 600;
            user-select: none;
        }
        .advanced-rules .rule-count { color: #6b7280; font-weight: 400; font-size: 0.85rem; }
        .rule-actions { display: flex; gap: 0.5rem; margin: 0.75rem 0 0.5rem; }
        .rule-action {
            font-size: 0.8rem; padding: 0.25rem 0.6rem; cursor: pointer;
            border: 1px solid var(--color-border, #e2e8f0); border-radius: 6px;
            background: var(--color-card, #fff); color: var(--color-text, #1e293b);
        }
        .rule-list { max-height: 320px; overflow-y: auto; }
        .rule-loading { color: #6b7280; font-size: 0.85rem; padding: 0.5rem 0; }
        .rule-row {
            display: flex; align-items: center; gap: 0.5rem;
            padding: 0.25rem 0; font-size: 0.85rem;
        }
        .rule-row .rule-ref { font-family: monospace; color: #6b7280; white-space: nowrap; }
        .rule-row .rule-name { flex: 1; min-width: 0; }
        .rule-row .severity {
            font-size: 0.625rem; padding: 0.1rem 0.4rem; border-radius: 4px;
            font-weight: 600; text-transform: uppercase; flex-shrink: 0;
        }
        .rule-row .severity.ERROR { background: #fee2e2; color: #991b1b; }
        .rule-row .severity.WARNING { background: #fef3c7; color: #92400e; }
        .rule-row .severity.INFO { background: #dbeafe; color: #1e40af; }
```

- [ ] **Step 3: Add the `currentIgnore`, `updateRuleCount`, and `populateRuleList` helpers**

Add these in the main `<script>`, right before the existing `function revalidateCurrent()` (so they're defined alongside the re-run hook):

```javascript
        // The ignore set = the references of the unchecked rule rows. The DOM is
        // the single source of truth; there is no parallel JS state to drift.
        function currentIgnore() {
            return [...document.querySelectorAll('#rule-list input[type="checkbox"]')]
                .filter(cb => !cb.checked)
                .map(cb => cb.value);
        }

        function updateRuleCount() {
            const boxes = [...document.querySelectorAll('#rule-list input[type="checkbox"]')];
            const el = document.getElementById('rule-select-count');
            if (el) el.textContent = `(${boxes.filter(b => b.checked).length} of ${boxes.length} enabled)`;
        }

        // Fetch the selected suite's rules from Pyodide and render a checkbox per rule
        // (all enabled). Called when Pyodide is ready and on every suite change.
        async function populateRuleList(suiteName) {
            const list = document.getElementById('rule-list');
            if (!list || !pyodide) return;
            list.innerHTML = '<div class="rule-loading">loading rules…</div>';
            pyodide.globals.set('rules_suite', suiteName);
            let rules;
            try {
                rules = JSON.parse(await pyodide.runPythonAsync('list_rules(rules_suite)'));
            } catch (e) {
                rules = [];
            }
            if (!Array.isArray(rules)) rules = [];  // {error: …} shape -> empty
            list.innerHTML = '';
            for (const r of rules) {
                const row = document.createElement('label');
                row.className = 'rule-row';
                row.title = r.description || '';
                const cb = document.createElement('input');
                cb.type = 'checkbox'; cb.checked = true; cb.value = r.reference;
                const ref = document.createElement('span'); ref.className = 'rule-ref'; ref.textContent = r.reference;
                const name = document.createElement('span'); name.className = 'rule-name'; name.textContent = r.name;
                const sev = document.createElement('span'); sev.className = 'severity ' + r.severity; sev.textContent = r.severity;
                row.append(cb, ref, name, sev);
                list.appendChild(row);
            }
            updateRuleCount();
        }
```

(`textContent` is used for all rule fields so suite-provided strings can never inject markup.)

- [ ] **Step 4: Verify the page still parses (no JS/Python syntax break)**

Run:

```bash
uv run --with playwright python -c "
from playwright.sync_api import sync_playwright
import pathlib
errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    try: pg.goto('file://'+str(pathlib.Path('docs/demo/index.html').resolve()), wait_until='domcontentloaded', timeout=8000)
    except Exception: pass
    pg.wait_for_timeout(800)
    print('details panel present:', pg.eval_on_selector_all('#advanced-rules', 'e=>e.length'))
    print('populateRuleList type:', pg.evaluate('typeof populateRuleList'))
    print('syntax/reference errors:', [e for e in errs if 'SyntaxError' in e or 'ReferenceError' in e] or 'NONE')
    b.close()
"
```
Expected: `details panel present: 1`, `populateRuleList type: function`, `syntax/reference errors: NONE`.

- [ ] **Step 5: Commit**

```bash
git add docs/demo/index.html
git commit -m "feat(demo): advanced rule-selection panel markup, styles, and populate helpers

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Demo wiring — thread ignore into runs, repopulate on suite change, re-run on toggle

**Files:**
- Modify: `docs/demo/index.html` (JS in the main `<script>`)

- [ ] **Step 1: Pass `currentIgnore()` into `validateBytes`**

In `validateBytes`, find:
```javascript
                pyodide.globals.set('selected_suite', suiteName || document.querySelector('input[name="suite"]:checked').value);

                const html = await pyodide.runPythonAsync(`
validate_file_bytes(file_bytes.to_py(), file_name, selected_suite)
                `);
```
Replace with:
```javascript
                pyodide.globals.set('selected_suite', suiteName || document.querySelector('input[name="suite"]:checked').value);
                pyodide.globals.set('selected_ignore', JSON.stringify(currentIgnore()));

                const html = await pyodide.runPythonAsync(`
validate_file_bytes(file_bytes.to_py(), file_name, selected_suite, selected_ignore)
                `);
```

- [ ] **Step 2: Pass `currentIgnore()` into `processFileFromUrl`**

In `processFileFromUrl`, find:
```javascript
                pyodide.globals.set('selected_suite', document.querySelector('input[name="suite"]:checked').value);

                const html = await pyodide.runPythonAsync(`
validate_file_url(file_url, selected_suite)
                `);
```
Replace with:
```javascript
                pyodide.globals.set('selected_suite', document.querySelector('input[name="suite"]:checked').value);
                pyodide.globals.set('selected_ignore', JSON.stringify(currentIgnore()));

                const html = await pyodide.runPythonAsync(`
validate_file_url(file_url, selected_suite, selected_ignore)
                `);
```

- [ ] **Step 3: Pass `currentIgnore()` into `fixAndDownload`**

In `fixAndDownload`, find:
```javascript
                if (lastBytes) {
                    pyodide.globals.set('fix_bytes', lastBytes);
                    pyodide.globals.set('fix_name', lastName || 'file.cdf');
                    pyodide.globals.set('fix_suite', suite);
                    resultJson = await pyodide.runPythonAsync('fix_file_bytes(fix_bytes.to_py(), fix_name, fix_suite)');
                } else if (lastUrl) {
                    pyodide.globals.set('fix_url', lastUrl);
                    pyodide.globals.set('fix_suite', suite);
                    resultJson = await pyodide.runPythonAsync('fix_file_url(fix_url, fix_suite)');
                } else {
```
Replace with:
```javascript
                pyodide.globals.set('fix_ignore', JSON.stringify(currentIgnore()));
                if (lastBytes) {
                    pyodide.globals.set('fix_bytes', lastBytes);
                    pyodide.globals.set('fix_name', lastName || 'file.cdf');
                    pyodide.globals.set('fix_suite', suite);
                    resultJson = await pyodide.runPythonAsync('fix_file_bytes(fix_bytes.to_py(), fix_name, fix_suite, fix_ignore)');
                } else if (lastUrl) {
                    pyodide.globals.set('fix_url', lastUrl);
                    pyodide.globals.set('fix_suite', suite);
                    resultJson = await pyodide.runPythonAsync('fix_file_url(fix_url, fix_suite, fix_ignore)');
                } else {
```

- [ ] **Step 4: Repopulate (reset) the rule list on suite change**

In the `DOMContentLoaded` handler, find the suite-change wiring added by the previous branch:
```javascript
            // Changing the suite re-runs the analysis on the loaded file automatically.
            document.querySelectorAll('input[name="suite"]').forEach((radio) => {
                radio.addEventListener('change', revalidateCurrent);
            });
```
Replace with:
```javascript
            // Changing the suite repopulates the rule list (all enabled) and re-runs.
            document.querySelectorAll('input[name="suite"]').forEach((radio) => {
                radio.addEventListener('change', async () => {
                    const suite = document.querySelector('input[name="suite"]:checked').value;
                    await populateRuleList(suite);
                    revalidateCurrent();
                });
            });

            // Toggling a rule (delegated) re-runs; Enable/Disable all set every box.
            document.getElementById('rule-list').addEventListener('change', (e) => {
                if (e.target.matches('input[type="checkbox"]')) {
                    updateRuleCount();
                    revalidateCurrent();
                }
            });
            function setAllRules(on) {
                document.querySelectorAll('#rule-list input[type="checkbox"]').forEach(cb => { cb.checked = on; });
                updateRuleCount();
                revalidateCurrent();
            }
            document.getElementById('rules-enable-all').addEventListener('click', () => setAllRules(true));
            document.getElementById('rules-disable-all').addEventListener('click', () => setAllRules(false));
```

- [ ] **Step 5: Populate the rule list once Pyodide is ready**

Find the post-init block where the version badge is set:
```javascript
                const version = await pyodide.runPythonAsync('astralint_version()');
                const badge = document.getElementById('version-badge');
                if (badge) { badge.textContent = 'v' + version; badge.hidden = false; }
```
Insert immediately after it:
```javascript
                await populateRuleList(document.querySelector('input[name="suite"]:checked').value);
```

(`autoRunFromQuery()` runs after this in the same init path; the panel is already populated by the time a deep-linked file validates.)

- [ ] **Step 6: Commit**

```bash
git add docs/demo/index.html
git commit -m "feat(demo): wire rule selection into validate/fix runs and suite changes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Verification — engine tests, lint, JS wiring, local serve

**Files:** none (verification only).

- [ ] **Step 1: Full engine test suite + lint**

Run: `uv run pytest -q && make lint`
Expected: all tests pass; lint clean. (If lint flags the new test, fix narrowly.)

- [ ] **Step 2: Behavioral JS-wiring check with stubs (no network)**

This stubs Pyodide and the validate functions to confirm the panel renders, `currentIgnore()` collects unchecked rows, a toggle re-runs with the right ignore array, and a suite change repopulates + resets.

```bash
uv run --with playwright python -c "
from playwright.sync_api import sync_playwright
import pathlib
url='file://'+str(pathlib.Path('docs/demo/index.html').resolve())
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page()
    try: pg.goto(url, wait_until='domcontentloaded', timeout=8000)
    except Exception: pass
    pg.wait_for_timeout(800)
    # Stub pyodide.list_rules and capture validate ignore.
    setup='''() => {
        window.__ignore=null;
        pyodide={ globals:{ _m:{}, set(k,v){this._m[k]=v;} },
                  runPythonAsync: async (code)=> {
                      if(code.includes('list_rules')) return JSON.stringify([
                        {reference:'ISTP-GA-001',name:'Mandatory',description:'d',severity:'ERROR'},
                        {reference:'ISTP-GA-016',name:'CDAWebReq',description:'d',severity:'WARNING'}]);
                      if(code.includes('validate_file_bytes')){ window.__ignore=pyodide.globals._m.selected_ignore; return '<div>ok</div>'; }
                      return ''; } };
    }'''
    pg.evaluate(setup)
    # populate
    pg.evaluate('async () => { await populateRuleList(\"ISTP\"); }')
    pg.wait_for_timeout(50)
    print('rows:', pg.eval_on_selector_all('#rule-list input[type=checkbox]','e=>e.length'))
    print('count text:', pg.inner_text('#rule-select-count'))
    # uncheck the 2nd rule, check currentIgnore
    ign=pg.evaluate('''() => {
        const boxes=[...document.querySelectorAll('#rule-list input[type=checkbox]')];
        boxes[1].checked=false; return currentIgnore(); }''')
    print('currentIgnore after uncheck:', ign)
    # simulate a loaded file + dispatch toggle -> validateBytes should get ignore
    fired=pg.evaluate('''async () => {
        lastBytes=new Uint8Array([1]); lastName='x.cdf'; lastUrl=null;
        const cb=document.querySelectorAll('#rule-list input[type=checkbox]')[1];
        cb.dispatchEvent(new Event('change',{bubbles:true}));
        await new Promise(r=>setTimeout(r,50));
        return window.__ignore; }''')
    print('ignore passed to validate:', fired)
    b.close()
"
```
Expected: `rows: 2`, `count text: (2 of 2 enabled)` initially, `currentIgnore after uncheck: ['ISTP-GA-016']`, and `ignore passed to validate: [\"ISTP-GA-016\"]` (a JSON string containing the unchecked reference).

- [ ] **Step 3: Serve the demo for the user to eyeball**

Note to the executor: the true Pyodide end-to-end needs network (`micropip.install('astralint…')`), so do not assert it headless. Instead start a local server and hand the URL to the user:

```bash
cd docs/demo && python3 -m http.server 8000
```
Tell the user to open `http://localhost:8000/`, load a CDF, expand "Advanced — rule selection", untick a rule, and confirm the report (and the proposed-fixes card) re-runs without it. Keep the checkout on this branch while the server runs (do side work in a worktree if needed).

- [ ] **Step 4: Final commit check**

Run: `git status --short`
Expected: only untracked throwaways (`report-preview.*`, `test.html`, `.gitignore.back`, `uv.lock`) remain unstaged; no tracked changes left uncommitted.

---

## Self-review notes

- **Spec coverage:** §1 engine `ignore` (Task 1); §2 demo Python `list_rules` + `ignore_json` (Task 2); §3 UI panel + populate/currentIgnore (Task 3) + wiring/suite-change-reset/threading (Task 4); Testing section (Task 5: engine pytest + Playwright stub check + local serve). Non-goals (URL/config persistence, CLI wiring, free-text) are intentionally absent.
- **Placeholder scan:** every code step shows full code; the only "verify" steps are concrete commands with expected output.
- **Type/name consistency:** `currentIgnore()`, `populateRuleList()`, `updateRuleCount()`, `setAllRules()` are defined in Task 3/4 and referenced consistently; `ignore_json` is the Python param name across `validate_file_bytes`/`validate_file_url`/`fix_file_bytes`/`fix_file_url`/`_converge_to_json`; the JS globals `selected_ignore`/`fix_ignore` carry `JSON.stringify(currentIgnore())`; `converge(..., ignore=...)` matches Task 1. Checkbox `value` = rule `reference`, which is what `ignore` matches on in `filter_rules`.
