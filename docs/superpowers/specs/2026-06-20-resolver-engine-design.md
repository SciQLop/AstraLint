# Resolver Engine — Design (Phase 1)

**Status:** approved design, implementation not started
**Owner:** Alexis Jeandet (LPP)
**Scope:** AstraLint deterministic correction/authoring engine, Phase 1 (no ML)
**Source:** `~/Downloads/HANDOVER_resolver_engine.md` (design intent), grounded by Phase-0 recon of the current codebase.

---

## 1. Goal

Assist users in fixing space-physics data files — both repairing existing/orphan CDFs and building new
calibration pipelines for new missions — by turning AstraLint validation failures into **proposed,
provenance-tagged attribute fixes**, auto-applying the safe deterministic ones, mutating the CDF in memory,
and re-validating until clean.

A fix's difficulty is resolved against whatever authoritative reference is available. Phase 1 implements the
**deterministic floor** (pure functions of CDF type and the variable reference graph). The ML/reference
layers are explicitly future work; the design leaves clean seams for them (§9).

## 2. Phase-0 findings that shaped this design

Confirmed against the current code:

- **Runtime is pure Python, already on Pyodide.** The validation core is Python (Pydantic v2, Jinja2,
  PyYAML, pycdfpp, astropy); the web build is Pyodide + `micropip.install('astralint')`. There is no
  native/Rust/C++ validation core. → **Decision: the resolver lives in Python inside AstraLint and the whole
  loop runs in one runtime via pycdfpp.** The handover's "single WASM runtime / no Pyodide" lean assumed a
  non-Python core; with a Python core, a wacdfpp-native path would require porting the resolver to TS/C++ and
  maintaining a second copy of the violation taxonomy — exactly what the handover forbids.
- **Violation taxonomy exists at rule granularity.** Rules carry stable IDs (`reference: "ISTP-VA-011"`).
  A failure is a `ValidationResult` leaf with `reference` (rule id), `severity`, `target` (cleaned path →
  `"var/attr"` or `"attr"`), `value` (the actual scalar), and a rendered prose `message`. The rule
  `reference` is too coarse to key fixes alone (one rule covers many attributes), so the resolver keys on
  **(attribute, scope)** parsed from `target`, with `reference` as an optional filter.
- **The File model is metadata-only and read-only.** `Variable` has `name, attributes, compression,
  data_type, record_variance, shape` — **no data arrays** (only `Attribute.values` carries values). Graph
  rules and type-only rules are fully supported; data-dependent resolvers (`FORMAT`, `MONOTON`,
  `SCALEMIN/MAX`) are **out of Phase 1** (they need the variable arrays the codec drops). There is no
  write-back path in AstraLint — mutation is done via pycdfpp.
- **Mutation surface.** pycdfpp (Python/Pyodide) exposes `save` + `_patch_add_variable`,
  `_patch_add_cdf_attribute`, `_patch_add_variable_attribute` — enough for the full mutate→save→re-validate
  loop in one runtime. (The Explorer's `wacdfpp` JS binding is currently read+save only — no write methods —
  so a wacdfpp-native loop would first need new bindings. Out of scope here.)

## 3. Locked decisions

| Decision | Choice |
|---|---|
| Runtime | Python resolver inside AstraLint; loop via pycdfpp; runs in Pyodide (already shipped) |
| Scope | Tier 1 + Tier 2 **no-data subset**; no File-model/codec changes |
| Deliverable | Propose **+ apply + convergence loop** → produces a corrected `.cdf`; Tier 3 staged, not auto-applied |
| Drive model | **Failure-driven post-pass**: `resolve(File, ValidationResultGroup)` keyed on `(attribute, scope)` |
| Registry | **Python Pydantic table**; each entry references its resolver function directly (no string dispatch) |

## 4. Architecture & module layout

A new self-contained package. **Zero changes to the rule engine, codecs, or File model.**

```
src/astralint/resolver/
  models.py          # Fix, ResolverEntry, ResolverOutput, Scope, ReferenceSource, ApplyPolicy
  registry.py        # REGISTRY: list[ResolverEntry] — the declarative table
  sources/
    type_rules.py    # Tier 1: fillval_by_type, scaletyp_default
    graph_rules.py   # Tier 2: depend0_finder, var_type_infer, display_type_infer (+ graph utils)
    pointers.py      # Tier 3: dangling-pointer detection + closest-name suggestion (stage-only)
  engine.py          # resolve(file, results) -> list[Fix]
  apply.py           # apply_fixes(cdf_bytes, fixes) -> bytes   (pycdfpp; re-fetch-after-mutate)
  loop.py            # converge(cdf_bytes, suite, ...) -> ConvergenceReport
```

### Data flow (the loop)

```
converge(cdf_bytes, suite, max_iter=10):
  loop until errors == 0 OR no-progress OR max_iter:
    file     = codec.load(cdf_bytes)
    results  = suite.run(file)
    fixes    = engine.resolve(file, results.failures_only())
    auto, staged = split(fixes)        # auto = always | (if_unique & not ambiguous)
    if not auto: break                 # converged or stuck
    cdf_bytes = apply.apply_fixes(cdf_bytes, auto)   # pycdfpp mutate→save
  return ConvergenceReport(iterations, applied[], remaining_failures[], staged[])
```

### How `engine.resolve` keys fixes

Walk failing `ValidationResult` leaves → parse `target` into `(variable, attribute)` + scope (reusing
`clean_target`/`build_context` from `assertions/base.py`) → registry lookup by `(attribute, scope)`,
filtered by `reference` if the entry pins one → call `entry.resolver(file, variable, attribute, failure)` →
wrap the `ResolverOutput` into a `Fix`. Highest-priority available source wins; dedupe per target.

## 5. Data model

```python
class Scope(str, Enum):
    VARIABLE = "variable"
    GLOBAL = "global"

class ReferenceSource(str, Enum):           # Phase-1 subset; extended in Phase 2 (§9)
    TYPE_RULE = "type_rule"
    GRAPH_RULE = "graph_rule"
    USER = "user"

class ApplyPolicy(str, Enum):
    ALWAYS = "always"
    IF_UNIQUE = "if_unique"
    NEVER = "never"

class ResolverEntry(BaseModel):             # one declarative registry row
    attribute: str                          # "FILLVAL", "DEPEND_0", ...
    scope: Scope
    trigger: str | None = None              # optional rule `reference` filter, e.g. "ISTP-VA-001"
    sources: list[ReferenceSource]          # priority chain (Phase 1: [TYPE_RULE] or [GRAPH_RULE])
    resolver: Callable                      # DIRECT function reference (not a string)
    auto_apply: ApplyPolicy
    confidence_default: float

class ResolverOutput(BaseModel):            # what a resolver fn returns (or None if it can't resolve)
    value: Any
    confidence: float | None = None         # overrides entry.confidence_default when set
    provenance_note: str
    ambiguous: bool = False                 # if_unique → stage when True
    alternatives: list[Any] = []            # candidate values when ambiguous (for staged suggestion)

class Fix(BaseModel):                       # the auditable unit
    target_path: str                        # "variables/Epoch/attributes/FILLVAL"
    variable: str | None
    attribute: str
    scope: Scope
    action: Literal["add", "set"]           # add = missing attr; set = present-but-wrong
    value: Any
    source: ReferenceSource
    confidence: float
    provenance_note: str
    auto: bool                              # decided by split(): always | (if_unique & not ambiguous)
```

Every `Fix` carries `{source, confidence, provenance_note}` so it is auditable and the future diff view can
colour/label it. The `numeric_or_physical` guard field is intentionally **not** added in Phase 1 (no model
source exists yet → YAGNI); its designated home is documented in §9.

## 6. Resolver catalog (Phase 1 — Tier 1 + 2, no-data)

Each row is one `ResolverEntry`; the resolver is a pure function of the `File` model.

| Attribute | Scope | Source | Logic | auto_apply |
|---|---|---|---|---|
| `FILLVAL` | variable | type_rule | ISTP default by `var.data_type`: `INT8`→−128, `INT16`→−32768, `INT32`→−2³¹, `INT64`/`TT2000`→−2⁶³, `FLOAT32/64`/`CDFEPOCH`→−1e31, `CDFEPOCH16`→(−1e31,−1e31), `CHAR`→blank | always |
| `SCALETYP` | variable | type_rule | `"linear"` | always |
| `VAR_TYPE` | variable | graph_rule | pointed-to by a `DEPEND_i` ⇒ `support_data`; by a `LABL_PTR_i` ⇒ `metadata`; numeric with own `DEPEND_0` ⇒ `data` | if_unique |
| `DEPEND_0` | variable | graph_rule | the unique time variable: CDF time `data_type`, equal record count (`shape[0]`), `VAR_TYPE=support_data`. Unique→auto; multiple→staged | if_unique |
| `DISPLAY_TYPE` | variable | graph_rule | 1-D record-varying ⇒ `time_series`; 2-D with `DEPEND_1` ⇒ `spectrogram` | if_unique |
| `DEPEND_i`/`LABL_PTR_i`/`UNIT_PTR`/`FORM_PTR`/`DELTA_*` | variable | graph_rule | **detect** dangling pointer; offer closest-name match (`difflib.get_close_matches` over variable names) as a suggestion | never (staged) |

**Excluded this slice (data-dependent — need the variable arrays the File model drops):** `FORMAT`,
`MONOTON`, `SCALEMIN/MAX`. They are left as explicit `# Phase-1b: needs data` stubs so the catalog gap is
visible, not silent.

**Implementation verification items (pin with tests before relying on them):**
- `var.shape[0]` is the record count for record-varying vars (the `DEPEND_0` record-count match depends on
  it).
- pycdfpp's overwrite path for an existing attribute value (`action="set"`). The visible patches are
  add-only; if there is no in-place set, `set` becomes remove + re-add. Most Phase-1 fixes are *missing*
  attributes (`action="add"`), so `set` is secondary — but it must be confirmed before use.

## 7. Mutation (`apply.py`) — pycdfpp hazards, enforced in code

- Most Phase-1 fixes are **missing** attributes → `action="add"` via the patched
  `add_variable_attribute`/`add_cdf_attribute`. `action="set"` overwrites a present-but-wrong value
  (pending the §6 verification of an in-place set path).
- **Re-fetch-after-mutate:** pycdfpp wrappers hold references into C++ containers; any structural add/remove
  invalidates cached handles. `apply_fixes` re-acquires the variable/attribute handle after every structural
  edit and never caches one across a mutation — documented inline with the *why*. All auto-fixes are applied
  in a single pass, then `save()→bytes` once.

## 8. Convergence loop (`loop.py`) — safety

- **Hard iteration cap** (default 10).
- **No-progress detection:** hash the set of failing `(reference, target)` pairs each pass; if the apply
  step does not shrink it, stop and report "stuck" rather than oscillate.
- Re-validation each pass catches **induced** violations (e.g. adding `DEPEND_0` exposes a downstream
  dimension/`VAR_TYPE` issue) — the reason for looping instead of one-shot.
- Auto-applied tiers are deterministic, so the loop is reproducible.

## 9. Phase-2 extension seam (AI suggestions — designed in, not built)

The architecture is AI-ready; Phase 2 is purely additive and touches no deterministic code path:

1. **A model is just another `ReferenceSource` + `ResolverEntry`.** Phase 2 adds `CORPUS_PRIOR` (and
   `MASTER`/`SPASE`/`PDS4`) to the enum and registers rows like
   `ResolverEntry(attribute="CATDESC", sources=[..., CORPUS_PRIOR], resolver=model_draft, auto_apply=NEVER)`.
   `engine.resolve` already walks the registry and calls whatever `resolver` it finds.
2. **The `sources` priority chain makes ML the floor automatically** — a model source only fires when no
   deterministic/reference source resolves (first-available-wins on an ordered list).
3. **`ResolverOutput.ambiguous` + `alternatives` is the disambiguation hook** — a model that *ranks* tied
   graph-rule candidates reorders `alternatives`; it never invents values.
4. **The staged-fix boundary is the cross-runtime injection point** — the loop emits staged fixes as plain
   JSON, so a model in a different runtime (e.g. Transformers.js in the Explorer) can produce candidate
   values for `auto_apply=NEVER` attributes and inject them as staged `Fix`es into the same approve→apply
   pipeline. `apply.py` only applies what a human approved; it is agnostic to a value's origin.
5. **Every `Fix` is labeled `source`/`confidence`/`provenance_note`,** so the diff view can distinguish an AI
   suggestion from a deterministic fix.

**Guard to add at the Phase-2 seam (enforced in code, not docs):** the handover's hard invariant that a model
may never resolve `numeric_or_physical` or identity/provenance fields (`UNITS`, `VALIDMIN/MAX`, `FILLVAL`,
`PI_name`, …). Designated home: a `numeric_or_physical: bool` flag on `ResolverEntry` plus a
registration/`split()` assertion that rejects `CORPUS_PRIOR` in `sources` whenever the flag is set. Not added
in Phase 1 (YAGNI), recorded here so it is not forgotten.

## 10. CLI surface

A new `fix` subcommand alongside `lint`/`config`/`list-suites`/`dump-file-model`, following the existing
patterns in `astralint.py`:

```bash
astralint fix <file.cdf> [--suite ISTP] [--apply auto|none] \
                         [--output fixed.cdf] [--format console|json]
```

- `--apply auto` (default): runs the convergence loop, auto-applies Tier 1/2, writes the corrected CDF to
  `--output` (default `<stem>.fixed.cdf`), reports staged Tier-3 suggestions (never written).
- `--apply none`: dry-run — lists proposed fixes with full provenance, writes nothing.
- **Report** (console + JSON, reusing the existing reporter style): per applied fix
  `{target · value · source · confidence · provenance_note}`, iteration count, before→after failure counts,
  and the staged-suggestions block. The JSON payload is the contract the future Explorer diff/staging view
  consumes — loop and report are decoupled from any UI.

## 11. Testing strategy (TDD — reproducer-first)

1. **Resolver unit tests** (the bulk): construct a `File`/`Variable` model directly with the deficiency,
   assert `ResolverOutput.value`/`source`/`confidence`/`ambiguous`. No real CDF needed. One per catalog row,
   including the `if_unique`-ambiguous branch (two candidate time vars → staged, not auto).
2. **Engine tests:** failure tree + File → expected `Fix` list (target parsing, registry keying, `reference`
   filter, per-target dedup/priority).
3. **Apply tests:** start from a real small CDF in `tests/resources/`, apply a fix via pycdfpp, `save→load`
   round-trip, assert the attribute landed *and* that handles were re-fetched (mutate two attrs in one pass).
4. **Loop tests:** a deliberately broken CDF (drop `FILLVAL`/`DEPEND_0`) → `converge` → assert errors drop /
   reach zero; plus explicit no-progress and iteration-cap tests pinning the safety guards.

`make lint` + `make test` clean before completion; the existing suite stays green (no engine changes).

## 12. Non-goals (Phase 1)

- No LLM/ML in the deterministic path (Phase 2, advisory-only).
- No data-dependent resolvers (`FORMAT`/`MONOTON`/`SCALEMIN/MAX`) — needs a File-model/codec extension first.
- No reference-source loaders (`master`/SPASE/PDS4) and no Production/Authoring regime checks yet.
- No wacdfpp write bindings / no Explorer UI integration — the JSON report is the forward contract.
- No File-model, codec, or rule-engine changes.
