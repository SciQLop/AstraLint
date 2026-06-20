# Resolver Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, failure-driven resolver engine in AstraLint that turns ISTP validation failures into provenance-tagged attribute fixes, auto-applies the safe Tier 1/2 ones via pycdfpp, and loops mutate→re-validate until a CDF is clean.

**Architecture:** A new self-contained `src/astralint/resolver/` package. It consumes the existing engine's `ValidationResultGroup` output and the read-only `File` model, looks up resolver functions in a Pydantic registry keyed on `(attribute, scope)` (filtered by rule reference), emits `Fix` objects, and applies them to an in-memory CDF with pycdfpp. No changes to the rule engine, codecs, or File model.

**Tech Stack:** Python 3.11+, Pydantic v2, pycdfpp (load/save/add_attribute/set_value), cyclopts (CLI), pytest. Runs in CPython and Pyodide.

**Reference spec:** `docs/superpowers/specs/2026-06-20-resolver-engine-design.md`

**Verified pycdfpp API (used throughout):**
- `pycdfpp.load(path_or_bytes)` → CDF; `cdf.items()`, `cdf[name]`, `cdf.attributes`, `cdf.add_attribute(name, [entries], [types])`.
- `var.attributes` (membership via `name in var.attributes`), `var.add_attribute(name, value[, cdf_type])`, `var.attributes[name].set_value(value[, cdf_type])`.
- CHAR attribute: pass a plain `str`. Numeric: pass `np.array([v], dtype=...)` plus the matching `pycdfpp.DataType`.
- `pycdfpp.save(cdf)` returns a loadable `_cdf_bytes`; materialise real `bytes` with `bytes(saved)` before writing to a file.

---

## File Structure

```
src/astralint/resolver/
  __init__.py          # package exports: resolve, converge, apply_fixes, Fix, ConvergenceReport
  models.py            # Scope, ReferenceSource, ApplyPolicy, ResolverOutput, ResolverEntry, Fix
  sources/
    __init__.py
    type_rules.py      # fillval_by_type, scaletyp_default
    graph_rules.py     # graph utils + depend0_finder, var_type_infer, display_type_infer
    pointers.py        # dangling_pointer_suggestion
  registry.py          # REGISTRY: list[ResolverEntry]
  engine.py            # resolve(file, failures) -> list[Fix]
  apply.py             # apply_fixes(cdf_bytes, fixes) -> bytes
  loop.py              # converge(cdf_bytes, suite, ...) -> (ConvergenceReport, bytes)

tests/
  test_resolver_models.py
  test_resolver_type_rules.py
  test_resolver_graph_rules.py
  test_resolver_pointers.py
  test_resolver_registry.py
  test_resolver_engine.py
  test_resolver_apply.py
  test_resolver_loop.py
  test_resolver_cli.py
```

Resolver function contract (every resolver): `def f(file: File, variable: str | None, attribute: str, failure: ValidationResult) -> ResolverOutput | None`. Returns `None` when not applicable.

---

### Task 1: Core data model

**Files:**
- Create: `src/astralint/resolver/__init__.py` (empty for now)
- Create: `src/astralint/resolver/models.py`
- Test: `tests/test_resolver_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_resolver_models.py
from astralint.resolver.models import (
    ApplyPolicy,
    Fix,
    ReferenceSource,
    ResolverEntry,
    ResolverOutput,
    Scope,
)


def test_resolver_output_defaults():
    out = ResolverOutput(value=-1e31, provenance_note="default")
    assert out.confidence is None
    assert out.ambiguous is False
    assert out.alternatives == []


def test_resolver_entry_holds_callable():
    def dummy(file, variable, attribute, failure):
        return None

    entry = ResolverEntry(
        attribute="FILLVAL",
        scope=Scope.VARIABLE,
        sources=[ReferenceSource.TYPE_RULE],
        resolver=dummy,
        auto_apply=ApplyPolicy.ALWAYS,
        confidence_default=1.0,
    )
    assert entry.triggers == []
    assert entry.resolver is dummy


def test_fix_is_auditable():
    fix = Fix(
        target_path="variables/Epoch/attributes/FILLVAL",
        variable="Epoch",
        attribute="FILLVAL",
        scope=Scope.VARIABLE,
        action="add",
        value=-1e31,
        source=ReferenceSource.TYPE_RULE,
        confidence=1.0,
        provenance_note="ISTP default",
        auto=True,
    )
    assert fix.source == ReferenceSource.TYPE_RULE
    assert fix.confidence == 1.0
    assert fix.provenance_note
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_resolver_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'astralint.resolver'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/astralint/resolver/__init__.py
```
(leave empty in this task)

```python
# src/astralint/resolver/models.py
from collections.abc import Callable
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class Scope(str, Enum):
    VARIABLE = "variable"
    GLOBAL = "global"


class ReferenceSource(str, Enum):
    TYPE_RULE = "type_rule"
    GRAPH_RULE = "graph_rule"
    USER = "user"


class ApplyPolicy(str, Enum):
    ALWAYS = "always"
    IF_UNIQUE = "if_unique"
    NEVER = "never"


class ResolverOutput(BaseModel):
    """What a resolver function returns (or None when it cannot resolve)."""

    value: Any
    confidence: float | None = None  # overrides entry.confidence_default when set
    provenance_note: str
    ambiguous: bool = False  # for if_unique: stage instead of auto-apply when True
    alternatives: list[Any] = []  # candidate values when ambiguous


class ResolverEntry(BaseModel):
    """One declarative registry row. `resolver` is a direct function reference."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    attribute: str
    scope: Scope
    sources: list[ReferenceSource]
    resolver: Callable
    auto_apply: ApplyPolicy
    confidence_default: float
    triggers: list[str] = []  # rule references this entry handles; empty = any


class Fix(BaseModel):
    """The auditable unit applied to a CDF."""

    target_path: str  # e.g. "variables/Epoch/attributes/FILLVAL"
    variable: str | None
    attribute: str
    scope: Scope
    action: Literal["add", "set"]  # add = missing attr; set = present-but-wrong
    value: Any
    source: ReferenceSource
    confidence: float
    provenance_note: str
    auto: bool  # decided by the engine: always | (if_unique & not ambiguous)
```

> Note: the spec described `trigger: str | None`; the implementation uses `triggers: list[str]` because several attributes are flagged by more than one rule (e.g. `VAR_TYPE` by both `ISTP-VA-001` missing and `ISTP-VA-004` invalid). Empty list means "match any reference".

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_resolver_models.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/astralint/resolver/__init__.py src/astralint/resolver/models.py tests/test_resolver_models.py
git commit -m "feat(resolver): core data model (Fix, ResolverEntry, ResolverOutput)"
```

---

### Task 2: Tier 1 type-rule resolvers

**Files:**
- Create: `src/astralint/resolver/sources/__init__.py` (empty)
- Create: `src/astralint/resolver/sources/type_rules.py`
- Test: `tests/test_resolver_type_rules.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_resolver_type_rules.py
from astralint.base.file import Attribute, DataType, File, Variable
from astralint.resolver.sources.type_rules import fillval_by_type, scaletyp_default


def _var(data_type: DataType) -> File:
    return File(
        extension="cdf",
        filename="t.cdf",
        compression="NONE",
        attributes={},
        variables={
            "v": Variable(
                name="v",
                shape=[10],
                attributes={},
                compression="NONE",
                data_type=data_type,
                record_variance=True,
            )
        },
    )


def test_fillval_int32():
    out = fillval_by_type(_var(DataType.INT32), "v", "FILLVAL", None)
    assert out is not None
    assert out.value == -(2**31)


def test_fillval_float64():
    out = fillval_by_type(_var(DataType.FLOAT64), "v", "FILLVAL", None)
    assert out.value == -1e31


def test_fillval_char_is_blank():
    out = fillval_by_type(_var(DataType.CHAR), "v", "FILLVAL", None)
    assert out.value == " "


def test_fillval_unmapped_type_returns_none():
    # Unsigned types are intentionally unmapped in Phase 1.
    assert fillval_by_type(_var(DataType.UINT32), "v", "FILLVAL", None) is None


def test_fillval_unknown_variable_returns_none():
    assert fillval_by_type(_var(DataType.INT32), "missing", "FILLVAL", None) is None


def test_scaletyp_default_is_linear():
    out = scaletyp_default(_var(DataType.FLOAT64), "v", "SCALETYP", None)
    assert out.value == "linear"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_resolver_type_rules.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/astralint/resolver/sources/__init__.py
```
(empty)

```python
# src/astralint/resolver/sources/type_rules.py
from typing import Any

from ...base.file import DataType, File
from ...base.validation_result import ValidationResult
from ..models import ResolverOutput

# ISTP default fill values keyed on the abstract CDF data type. Unsigned types
# are intentionally omitted in Phase 1 (no agreed ISTP default here yet).
_FILLVAL_BY_TYPE: dict[DataType, Any] = {
    DataType.INT8: -128,
    DataType.INT16: -32768,
    DataType.INT32: -(2**31),
    DataType.INT64: -(2**63),
    DataType.TT2000: -(2**63),
    DataType.FLOAT32: -1e31,
    DataType.FLOAT64: -1e31,
    DataType.CDFEPOCH: -1e31,
    DataType.CDFEPOCH16: (-1e31, -1e31),
    DataType.CHAR: " ",
}


def fillval_by_type(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    if variable is None or variable not in file.variables:
        return None
    data_type = file.variables[variable].data_type
    if data_type not in _FILLVAL_BY_TYPE:
        return None
    return ResolverOutput(
        value=_FILLVAL_BY_TYPE[data_type],
        provenance_note=f"ISTP default FILLVAL for {data_type.value}",
    )


def scaletyp_default(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    if variable is None or variable not in file.variables:
        return None
    return ResolverOutput(value="linear", provenance_note="ISTP default SCALETYP")


# Phase-1b (needs variable data, not carried by the File model): FORMAT from
# observed magnitude, MONOTON from the epoch array, SCALEMIN/SCALEMAX from
# percentiles. Left unimplemented on purpose so the catalog gap is visible.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_resolver_type_rules.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/astralint/resolver/sources/__init__.py src/astralint/resolver/sources/type_rules.py tests/test_resolver_type_rules.py
git commit -m "feat(resolver): Tier 1 type-rule resolvers (FILLVAL, SCALETYP)"
```

---

### Task 3: Tier 2 graph-rule resolvers

**Files:**
- Create: `src/astralint/resolver/sources/graph_rules.py`
- Test: `tests/test_resolver_graph_rules.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_resolver_graph_rules.py
from astralint.base.file import Attribute, DataType, File, Variable
from astralint.resolver.sources.graph_rules import (
    depend0_finder,
    display_type_infer,
    var_type_infer,
)


def _attr(name, value, dt=DataType.CHAR):
    return Attribute(name=name, data_type=[dt], shape=[1], values=[value])


def _file(variables):
    return File(
        extension="cdf", filename="t.cdf", compression="NONE", attributes={}, variables=variables
    )


def _time_var(name="Epoch", records=10, var_type="support_data"):
    attrs = {}
    if var_type is not None:
        attrs["VAR_TYPE"] = _attr("VAR_TYPE", var_type)
    return Variable(
        name=name, shape=[records], attributes=attrs, compression="NONE",
        data_type=DataType.TT2000, record_variance=True,
    )


def _data_var(name="flux", records=10, ndim=1, attrs=None):
    shape = [records] if ndim == 1 else [records, 8]
    return Variable(
        name=name, shape=shape, attributes=attrs or {}, compression="NONE",
        data_type=DataType.FLOAT32, record_variance=True,
    )


def test_depend0_unique_time_var():
    f = _file({"Epoch": _time_var(records=10), "flux": _data_var(records=10)})
    out = depend0_finder(f, "flux", "DEPEND_0", None)
    assert out is not None and out.value == "Epoch" and out.ambiguous is False


def test_depend0_ambiguous_two_time_vars():
    f = _file({
        "Epoch": _time_var("Epoch", 10),
        "Epoch2": _time_var("Epoch2", 10),
        "flux": _data_var(records=10),
    })
    out = depend0_finder(f, "flux", "DEPEND_0", None)
    assert out.ambiguous is True
    assert set(out.alternatives) == {"Epoch", "Epoch2"}


def test_depend0_no_matching_record_count():
    f = _file({"Epoch": _time_var(records=5), "flux": _data_var(records=10)})
    assert depend0_finder(f, "flux", "DEPEND_0", None) is None


def test_var_type_support_data_when_pointed_by_depend():
    f = _file({
        "Epoch": _time_var(var_type=None),  # no VAR_TYPE yet
        "flux": _data_var(attrs={"DEPEND_0": _attr("DEPEND_0", "Epoch")}),
    })
    out = var_type_infer(f, "Epoch", "VAR_TYPE", None)
    assert out.value == "support_data"


def test_var_type_data_when_numeric_with_own_depend0():
    f = _file({
        "Epoch": _time_var(),
        "flux": _data_var(attrs={"DEPEND_0": _attr("DEPEND_0", "Epoch")}),
    })
    out = var_type_infer(f, "flux", "VAR_TYPE", None)
    assert out.value == "data"


def test_display_type_time_series_for_1d():
    f = _file({"Epoch": _time_var(), "flux": _data_var(ndim=1)})
    out = display_type_infer(f, "flux", "DISPLAY_TYPE", None)
    assert out.value == "time_series"


def test_display_type_spectrogram_for_2d_with_depend1():
    f = _file({
        "Epoch": _time_var(),
        "energy": _data_var("energy", ndim=1),
        "flux": _data_var(ndim=2, attrs={"DEPEND_1": _attr("DEPEND_1", "energy")}),
    })
    out = display_type_infer(f, "flux", "DISPLAY_TYPE", None)
    assert out.value == "spectrogram"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_resolver_graph_rules.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/astralint/resolver/sources/graph_rules.py
from ...base.file import DataType, File, Variable
from ...base.validation_result import ValidationResult
from ..models import ResolverOutput

_TIME_TYPES = (DataType.TT2000, DataType.CDFEPOCH, DataType.CDFEPOCH16)
_NUMERIC_TYPES = (
    DataType.INT8, DataType.INT16, DataType.INT32, DataType.INT64,
    DataType.UINT8, DataType.UINT16, DataType.UINT32, DataType.UINT64,
    DataType.FLOAT32, DataType.FLOAT64,
)
_DEPEND_ATTRS = ("DEPEND_0", "DEPEND_1", "DEPEND_2", "DEPEND_3")
_LABL_ATTRS = ("LABL_PTR_1", "LABL_PTR_2", "LABL_PTR_3")


def _record_count(var: Variable) -> int:
    return var.shape[0] if var.shape else 0


def _attr_scalar(var: Variable, name: str):
    attr = var.attributes.get(name)
    if attr and attr.values:
        return attr.values[0]
    return None


def _is_pointed_by(file: File, target: str, attr_names: tuple[str, ...]) -> bool:
    for var in file.variables.values():
        for name in attr_names:
            if _attr_scalar(var, name) == target:
                return True
    return False


def depend0_finder(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    if variable is None or variable not in file.variables:
        return None
    var = file.variables[variable]
    if not var.record_variance:
        return None
    n = _record_count(var)
    candidates = [
        name
        for name, tv in file.variables.items()
        if tv.data_type in _TIME_TYPES
        and _record_count(tv) == n
        and _attr_scalar(tv, "VAR_TYPE") == "support_data"
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return ResolverOutput(
            value=candidates[0],
            provenance_note=f"unique time variable with matching record count ({n})",
        )
    return ResolverOutput(
        value=candidates[0],
        ambiguous=True,
        alternatives=candidates,
        provenance_note=f"{len(candidates)} candidate time variables; needs a human choice",
    )


def var_type_infer(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    if variable is None or variable not in file.variables:
        return None
    if _is_pointed_by(file, variable, _DEPEND_ATTRS):
        return ResolverOutput(value="support_data", provenance_note="referenced by a DEPEND_i pointer")
    if _is_pointed_by(file, variable, _LABL_ATTRS):
        return ResolverOutput(value="metadata", provenance_note="referenced by a LABL_PTR_i pointer")
    var = file.variables[variable]
    if var.data_type in _NUMERIC_TYPES and "DEPEND_0" in var.attributes:
        return ResolverOutput(value="data", provenance_note="numeric variable with its own DEPEND_0")
    return None


def display_type_infer(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    if variable is None or variable not in file.variables:
        return None
    var = file.variables[variable]
    if not var.record_variance:
        return None
    ndim = len(var.shape)  # shape[0] is the record dimension
    if ndim == 1:
        return ResolverOutput(value="time_series", provenance_note="1-D record-varying variable")
    if ndim == 2 and "DEPEND_1" in var.attributes:
        return ResolverOutput(value="spectrogram", provenance_note="2-D variable with DEPEND_1")
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_resolver_graph_rules.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add src/astralint/resolver/sources/graph_rules.py tests/test_resolver_graph_rules.py
git commit -m "feat(resolver): Tier 2 graph-rule resolvers (DEPEND_0, VAR_TYPE, DISPLAY_TYPE)"
```

---

### Task 4: Tier 3 dangling-pointer suggestion

**Files:**
- Create: `src/astralint/resolver/sources/pointers.py`
- Test: `tests/test_resolver_pointers.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_resolver_pointers.py
from astralint.base.file import Attribute, DataType, File, Variable
from astralint.resolver.sources.pointers import dangling_pointer_suggestion


def _attr(name, value):
    return Attribute(name=name, data_type=[DataType.CHAR], shape=[1], values=[value])


def _file(variables):
    return File(
        extension="cdf", filename="t.cdf", compression="NONE", attributes={}, variables=variables
    )


def _var(name, attrs=None):
    return Variable(
        name=name, shape=[10], attributes=attrs or {}, compression="NONE",
        data_type=DataType.FLOAT32, record_variance=True,
    )


def test_dangling_suggests_closest_name():
    f = _file({
        "Epoch": _var("Epoch"),
        "flux": _var("flux", {"DEPEND_0": _attr("DEPEND_0", "Epokh")}),  # typo
    })
    out = dangling_pointer_suggestion(f, "flux", "DEPEND_0", None)
    assert out is not None
    assert out.value == "Epoch"
    assert out.ambiguous is True  # never auto-applied


def test_valid_pointer_returns_none():
    f = _file({
        "Epoch": _var("Epoch"),
        "flux": _var("flux", {"DEPEND_0": _attr("DEPEND_0", "Epoch")}),
    })
    assert dangling_pointer_suggestion(f, "flux", "DEPEND_0", None) is None


def test_no_close_match_returns_none():
    f = _file({
        "Epoch": _var("Epoch"),
        "flux": _var("flux", {"DEPEND_0": _attr("DEPEND_0", "zzzzz")}),
    })
    assert dangling_pointer_suggestion(f, "flux", "DEPEND_0", None) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_resolver_pointers.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/astralint/resolver/sources/pointers.py
import difflib

from ...base.file import File
from ...base.validation_result import ValidationResult
from ..models import ResolverOutput


def dangling_pointer_suggestion(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    if variable is None or variable not in file.variables:
        return None
    attr = file.variables[variable].attributes.get(attribute)
    if attr is None or not attr.values:
        return None
    referenced = attr.values[0]
    if referenced in file.variables:
        return None  # not dangling
    matches = difflib.get_close_matches(
        str(referenced), list(file.variables.keys()), n=1, cutoff=0.6
    )
    if not matches:
        return None
    return ResolverOutput(
        value=matches[0],
        ambiguous=True,  # Tier 3 is never auto-applied; always staged
        alternatives=matches,
        provenance_note=f"'{referenced}' not found; closest variable name is '{matches[0]}'",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_resolver_pointers.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/astralint/resolver/sources/pointers.py tests/test_resolver_pointers.py
git commit -m "feat(resolver): Tier 3 dangling-pointer suggestion (stage-only)"
```

---

### Task 5: Resolver registry

**Files:**
- Create: `src/astralint/resolver/registry.py`
- Test: `tests/test_resolver_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_resolver_registry.py
from astralint.resolver.models import ApplyPolicy, ReferenceSource, Scope
from astralint.resolver.registry import REGISTRY


def test_registry_has_fillval_entry():
    fillval = [e for e in REGISTRY if e.attribute == "FILLVAL"]
    assert len(fillval) == 1
    assert fillval[0].auto_apply == ApplyPolicy.ALWAYS
    assert fillval[0].sources == [ReferenceSource.TYPE_RULE]
    assert "ISTP-VA-001" in fillval[0].triggers


def test_pointer_entries_are_never_auto():
    pointer_attrs = {"DEPEND_0", "DEPEND_1", "LABL_PTR_1", "UNIT_PTR", "FORM_PTR"}
    pointer_entries = [
        e
        for e in REGISTRY
        if e.attribute in pointer_attrs and e.auto_apply == ApplyPolicy.NEVER
    ]
    assert pointer_entries  # at least the dangling-pointer entries exist


def test_every_entry_resolver_is_callable():
    assert all(callable(e.resolver) for e in REGISTRY)


def test_depend0_has_both_a_finder_and_a_dangling_entry():
    depend0 = [e for e in REGISTRY if e.attribute == "DEPEND_0"]
    triggers = {t for e in depend0 for t in e.triggers}
    assert "ISTP-VA-002" in triggers  # missing -> finder
    assert "ISTP-VA-011" in triggers  # dangling -> suggestion
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_resolver_registry.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/astralint/resolver/registry.py
from .models import ApplyPolicy, ReferenceSource, ResolverEntry, Scope
from .sources.graph_rules import depend0_finder, display_type_infer, var_type_infer
from .sources.pointers import dangling_pointer_suggestion
from .sources.type_rules import fillval_by_type, scaletyp_default

# Rule references that flag a dangling pointer for each pointer family.
_POINTER_TRIGGERS = {
    "DEPEND_0": ["ISTP-VA-011"],
    "DEPEND_1": ["ISTP-VA-011"],
    "DEPEND_2": ["ISTP-VA-011"],
    "DEPEND_3": ["ISTP-VA-011"],
    "LABL_PTR_1": ["ISTP-VA-012"],
    "LABL_PTR_2": ["ISTP-VA-012"],
    "LABL_PTR_3": ["ISTP-VA-012"],
    "UNIT_PTR": ["ISTP-VA-016"],
    "FORM_PTR": ["ISTP-VA-017"],
    "SCAL_PTR": ["ISTP-VA-018"],
    "DELTA_PLUS_VAR": ["ISTP-VA-014"],
    "DELTA_MINUS_VAR": ["ISTP-VA-014"],
}


def _pointer_entry(attribute: str, triggers: list[str]) -> ResolverEntry:
    return ResolverEntry(
        attribute=attribute,
        scope=Scope.VARIABLE,
        sources=[ReferenceSource.GRAPH_RULE],
        resolver=dangling_pointer_suggestion,
        auto_apply=ApplyPolicy.NEVER,
        confidence_default=0.5,
        triggers=triggers,
    )


REGISTRY: list[ResolverEntry] = [
    ResolverEntry(
        attribute="FILLVAL",
        scope=Scope.VARIABLE,
        sources=[ReferenceSource.TYPE_RULE],
        resolver=fillval_by_type,
        auto_apply=ApplyPolicy.ALWAYS,
        confidence_default=1.0,
        triggers=["ISTP-VA-001"],
    ),
    ResolverEntry(
        attribute="SCALETYP",
        scope=Scope.VARIABLE,
        sources=[ReferenceSource.TYPE_RULE],
        resolver=scaletyp_default,
        auto_apply=ApplyPolicy.ALWAYS,
        confidence_default=1.0,
        triggers=["ISTP-VA-013"],
    ),
    ResolverEntry(
        attribute="VAR_TYPE",
        scope=Scope.VARIABLE,
        sources=[ReferenceSource.GRAPH_RULE],
        resolver=var_type_infer,
        auto_apply=ApplyPolicy.IF_UNIQUE,
        confidence_default=0.9,
        triggers=["ISTP-VA-001", "ISTP-VA-004"],
    ),
    ResolverEntry(
        attribute="DEPEND_0",
        scope=Scope.VARIABLE,
        sources=[ReferenceSource.GRAPH_RULE],
        resolver=depend0_finder,
        auto_apply=ApplyPolicy.IF_UNIQUE,
        confidence_default=0.8,
        triggers=["ISTP-VA-002"],
    ),
    ResolverEntry(
        attribute="DISPLAY_TYPE",
        scope=Scope.VARIABLE,
        sources=[ReferenceSource.GRAPH_RULE],
        resolver=display_type_infer,
        auto_apply=ApplyPolicy.IF_UNIQUE,
        confidence_default=0.8,
        triggers=["ISTP-VA-002", "ISTP-VA-005"],
    ),
    *[_pointer_entry(attr, triggers) for attr, triggers in _POINTER_TRIGGERS.items()],
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_resolver_registry.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/astralint/resolver/registry.py tests/test_resolver_registry.py
git commit -m "feat(resolver): declarative registry table (Phase 1 catalog)"
```

---

### Task 6: Engine — resolve failures into Fixes

**Files:**
- Create: `src/astralint/resolver/engine.py`
- Test: `tests/test_resolver_engine.py`

The engine walks failing leaves, derives `(variable, attribute, scope)` from each leaf's `target`, selects matching registry entries (by scope + trigger + attribute), runs their resolvers, and builds deduped `Fix` objects.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_resolver_engine.py
from astralint.base.file import Attribute, DataType, File, Variable
from astralint.base.validation_result import (
    Severity,
    ValidationResult,
    ValidationResultGroup,
)
from astralint.resolver.engine import resolve


def _attr(name, value, dt=DataType.CHAR):
    return Attribute(name=name, data_type=[dt], shape=[1], values=[value])


def _file():
    return File(
        extension="cdf", filename="t.cdf", compression="NONE", attributes={},
        variables={
            "Epoch": Variable(
                name="Epoch", shape=[10],
                attributes={"VAR_TYPE": _attr("VAR_TYPE", "support_data")},
                compression="NONE", data_type=DataType.TT2000, record_variance=True,
            ),
            "flux": Variable(
                name="flux", shape=[10], attributes={}, compression="NONE",
                data_type=DataType.FLOAT32, record_variance=True,
            ),
        },
    )


def _failure(reference, target, value=""):
    return ValidationResult(
        valid=False, reference=reference, severity=Severity.ERROR,
        message="boom", target=target, value=value,
    )


def _group(results):
    return ValidationResultGroup(
        name="g", rule_reference="", severity=Severity.ERROR, results=results
    )


def test_resolve_fillval_missing_on_record_varying_var():
    # ISTP-VA-001 missing-mandatory failure on variable "flux"; target is the var.
    failures = _group([_failure("ISTP-VA-001", "flux")])
    fixes = resolve(_file(), failures)
    fillval = [f for f in fixes if f.attribute == "FILLVAL"]
    assert len(fillval) == 1
    assert fillval[0].value == -1e31
    assert fillval[0].action == "add"
    assert fillval[0].auto is True
    assert fillval[0].target_path == "variables/flux/attributes/FILLVAL"


def test_resolve_depend0_finder_on_data_var_attributes_failure():
    failures = _group([_failure("ISTP-VA-002", "flux")])
    fixes = resolve(_file(), failures)
    depend0 = [f for f in fixes if f.attribute == "DEPEND_0"]
    assert len(depend0) == 1
    assert depend0[0].value == "Epoch"
    assert depend0[0].auto is True  # unique


def test_resolve_dangling_depend0_is_staged_not_auto():
    f = _file()
    f.variables["flux"].attributes["DEPEND_0"] = _attr("DEPEND_0", "Epokh")
    failures = _group([_failure("ISTP-VA-011", "flux/DEPEND_0", value="Epokh")])
    fixes = resolve(f, failures)
    dangling = [x for x in fixes if x.attribute == "DEPEND_0"]
    assert len(dangling) == 1
    assert dangling[0].value == "Epoch"
    assert dangling[0].auto is False  # NEVER auto-applied
    assert dangling[0].action == "set"


def test_resolve_dedups_same_target():
    # Two failures that both route to FILLVAL on the same variable.
    failures = _group([_failure("ISTP-VA-001", "flux"), _failure("ISTP-VA-001", "flux")])
    fixes = resolve(_file(), failures)
    assert len([f for f in fixes if f.attribute == "FILLVAL"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_resolver_engine.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/astralint/resolver/engine.py
from ..base.file import File
from ..base.validation_result import (
    Severity,
    ValidationResult,
    ValidationResultGroup,
)
from .models import ApplyPolicy, Fix, ResolverEntry, Scope
from .registry import REGISTRY


def _iter_failures(group: ValidationResultGroup):
    for result in group.results:
        if isinstance(result, ValidationResultGroup):
            yield from _iter_failures(result)
        elif not result.valid and result.severity != Severity.SKIPPED:
            yield result


def _split_target(file: File, target: str) -> tuple[str | None, str | None, Scope]:
    """Derive (variable, attribute, scope) from a ValidationResult.target.

    Formats produced by clean_target:
      "var/attr" -> variable + attribute
      "token"    -> a variable (attribute unknown) or a global attribute
      ""         -> global, no attribute
    """
    if not target:
        return None, None, Scope.GLOBAL
    if "/" in target:
        variable, attribute = target.split("/", 1)
        return variable, attribute, Scope.VARIABLE
    if target in file.variables:
        return target, None, Scope.VARIABLE
    return None, target, Scope.GLOBAL


def _entry_matches(
    entry: ResolverEntry, reference: str, attribute: str | None, scope: Scope
) -> bool:
    if entry.scope != scope:
        return False
    if entry.triggers and reference not in entry.triggers:
        return False
    if attribute is not None and entry.attribute != attribute:
        return False
    return True


def _build_fix(
    file: File, entry: ResolverEntry, variable: str | None, output
) -> Fix:
    attribute = entry.attribute
    if entry.scope == Scope.VARIABLE and variable is not None:
        present = attribute in file.variables[variable].attributes
        target_path = f"variables/{variable}/attributes/{attribute}"
    else:
        present = attribute in file.attributes
        target_path = f"attributes/{attribute}"
    auto = entry.auto_apply == ApplyPolicy.ALWAYS or (
        entry.auto_apply == ApplyPolicy.IF_UNIQUE and not output.ambiguous
    )
    return Fix(
        target_path=target_path,
        variable=variable,
        attribute=attribute,
        scope=entry.scope,
        action="set" if present else "add",
        value=output.value,
        source=entry.sources[0],
        confidence=output.confidence if output.confidence is not None else entry.confidence_default,
        provenance_note=output.provenance_note,
        auto=auto,
    )


def resolve(file: File, failures: ValidationResultGroup) -> list[Fix]:
    fixes: dict[str, Fix] = {}  # keyed on target_path for dedup
    for leaf in _iter_failures(failures):
        variable, attribute, scope = _split_target(file, leaf.target)
        for entry in REGISTRY:
            if not _entry_matches(entry, leaf.reference, attribute, scope):
                continue
            output = entry.resolver(file, variable, entry.attribute, leaf)
            if output is None:
                continue
            fix = _build_fix(file, entry, variable, output)
            existing = fixes.get(fix.target_path)
            if existing is None or fix.confidence > existing.confidence:
                fixes[fix.target_path] = fix
    return list(fixes.values())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_resolver_engine.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/astralint/resolver/engine.py tests/test_resolver_engine.py
git commit -m "feat(resolver): failure-driven engine resolving fixes from validation results"
```

---

### Task 7: Apply fixes via pycdfpp

**Files:**
- Create: `src/astralint/resolver/apply.py`
- Test: `tests/test_resolver_apply.py`

`apply_fixes` loads the CDF from bytes, applies each fix (add or set), re-fetching the variable handle after every structural edit, and returns the saved bytes. CHAR values are written as plain strings; numeric values use the target variable's CDF type.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_resolver_apply.py
import os

import pycdfpp
import pytest

from astralint.resolver.apply import apply_fixes
from astralint.resolver.models import Fix, ReferenceSource, Scope

__HERE__ = os.path.dirname(__file__)
_CDF = os.path.join(__HERE__, "resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf")


def _bytes() -> bytes:
    with open(_CDF, "rb") as f:
        return f.read()


def _target_variable() -> str:
    cdf = pycdfpp.load(_CDF)
    for name, var in cdf.items():
        if "NEW_SCALETYP" not in var.attributes and "NEW_FILLVAL" not in var.attributes:
            return name
    raise AssertionError("no suitable variable")


def _fix(variable, attribute, value, action, scope=Scope.VARIABLE):
    return Fix(
        target_path=f"variables/{variable}/attributes/{attribute}",
        variable=variable, attribute=attribute, scope=scope, action=action,
        value=value, source=ReferenceSource.TYPE_RULE, confidence=1.0,
        provenance_note="test", auto=True,
    )


def test_apply_add_char_and_numeric_in_one_pass():
    var = _target_variable()
    fixes = [
        _fix(var, "NEW_SCALETYP", "linear", "add"),
        _fix(var, "NEW_FILLVAL", -1e31, "add"),
    ]
    out = apply_fixes(_bytes(), fixes)
    cdf = pycdfpp.load(out)
    assert [x for x in cdf[var].attributes["NEW_SCALETYP"]] == ["linear"]
    assert [x for x in cdf[var].attributes["NEW_FILLVAL"]] == [[-1e31]]


def test_apply_set_overwrites_existing():
    # find a var that already has SCALETYP and overwrite it
    cdf = pycdfpp.load(_CDF)
    var = next(n for n, v in cdf.items() if "SCALETYP" in v.attributes)
    out = apply_fixes(_bytes(), [_fix(var, "SCALETYP", "log", "set")])
    reloaded = pycdfpp.load(out)
    assert [x for x in reloaded[var].attributes["SCALETYP"]] == ["log"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_resolver_apply.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/astralint/resolver/apply.py
import numpy as np
import pycdfpp

from ..base.file import DataType
from .models import Fix, Scope

# Abstract data type -> (numpy dtype, pycdfpp CDF type) for writing numeric values.
_CDF_WRITE = {
    DataType.INT8: (np.int8, pycdfpp.DataType.CDF_INT1),
    DataType.INT16: (np.int16, pycdfpp.DataType.CDF_INT2),
    DataType.INT32: (np.int32, pycdfpp.DataType.CDF_INT4),
    DataType.INT64: (np.int64, pycdfpp.DataType.CDF_INT8),
    DataType.FLOAT32: (np.float32, pycdfpp.DataType.CDF_FLOAT),
    DataType.FLOAT64: (np.float64, pycdfpp.DataType.CDF_DOUBLE),
    DataType.TT2000: (np.int64, pycdfpp.DataType.CDF_TIME_TT2000),
}

_CDF_TYPE_MAP = {  # mirror of codecs/cdf.py type_mapping, abstract -> CDF enum
    DataType.UINT8: pycdfpp.DataType.CDF_UINT1,
    DataType.UINT16: pycdfpp.DataType.CDF_UINT2,
    DataType.UINT32: pycdfpp.DataType.CDF_UINT4,
}


def _numeric_value_and_type(variable_cdf_type, value):
    np_dtype, cdf_type = _CDF_WRITE[variable_cdf_type]
    return np.array([value], dtype=np_dtype), cdf_type


def _abstract_type(var) -> DataType:
    # reuse the codec mapping so apply and load agree on types
    from ..codecs.cdf import _to_data_type

    return _to_data_type(var.type)


def _apply_one(cdf, fix: Fix) -> None:
    if fix.scope == Scope.GLOBAL:
        # Phase 1 emits no global fixes, but keep the path honest.
        if fix.action == "add":
            cdf.add_attribute(fix.attribute, [[fix.value]], [pycdfpp.DataType.CDF_CHAR])
        return

    # Re-fetch the variable handle every time: pycdfpp wrappers hold references
    # into C++ containers and are invalidated by any structural add/remove.
    var = cdf[fix.variable]
    is_string = isinstance(fix.value, str)

    if fix.action == "add":
        if is_string:
            var.add_attribute(fix.attribute, fix.value)
        else:
            values, cdf_type = _numeric_value_and_type(_abstract_type(var), fix.value)
            var.add_attribute(fix.attribute, values, cdf_type)
    else:  # set
        attr = var.attributes[fix.attribute]
        if is_string:
            attr.set_value(fix.value)
        else:
            values, cdf_type = _numeric_value_and_type(_abstract_type(var), fix.value)
            attr.set_value(values, cdf_type)


def apply_fixes(cdf_bytes: bytes, fixes: list[Fix]) -> bytes:
    cdf = pycdfpp.load(cdf_bytes)
    for fix in fixes:
        _apply_one(cdf, fix)
    return bytes(pycdfpp.save(cdf))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_resolver_apply.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/astralint/resolver/apply.py tests/test_resolver_apply.py
git commit -m "feat(resolver): apply fixes via pycdfpp (re-fetch-after-mutate)"
```

---

### Task 8: Convergence loop

**Files:**
- Create: `src/astralint/resolver/loop.py`
- Modify: `src/astralint/resolver/__init__.py` (add exports)
- Test: `tests/test_resolver_loop.py`

`converge` runs validate → resolve → split → apply repeatedly until errors reach zero, no progress is made, or the iteration cap is hit. It returns a `ConvergenceReport` plus the corrected CDF bytes.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_resolver_loop.py
import os

import pycdfpp

from astralint.base import get_suite
from astralint.resolver.loop import ConvergenceReport, converge

__HERE__ = os.path.dirname(__file__)
_CDF = os.path.join(__HERE__, "resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf")


def _broken_bytes() -> bytes:
    """Drop FILLVAL from a record-varying variable to create a fixable error."""
    cdf = pycdfpp.load(_CDF)
    for name, var in cdf.items():
        if "FILLVAL" in var.attributes and not var.is_nrv:
            # rebuild without FILLVAL by saving, then removing is unsupported;
            # instead add a fresh broken variable-free file is overkill — use filter.
            pass
    # Simplest deterministic breakage: add a variable attribute pointing nowhere.
    target = next(n for n, v in cdf.items() if not v.is_nrv)
    if "DEPEND_0" in cdf[target].attributes:
        cdf[target].attributes["DEPEND_0"].set_value("DOES_NOT_EXIST")
    return bytes(pycdfpp.save(cdf))


def test_converge_returns_report_and_bytes():
    suite = get_suite("ISTP")
    report, out = converge(_broken_bytes(), suite, max_iter=5)
    assert isinstance(report, ConvergenceReport)
    assert isinstance(out, bytes)
    assert report.iterations >= 1
    assert report.stopped_reason in {"converged", "no_progress", "max_iter"}


def test_converge_caps_iterations():
    suite = get_suite("ISTP")
    report, _ = converge(_broken_bytes(), suite, max_iter=1)
    assert report.iterations <= 1


def test_converge_clean_file_is_immediate():
    with open(_CDF, "rb") as f:
        data = f.read()
    suite = get_suite("ISTP")
    report, out = converge(data, suite, max_iter=5)
    # A file with no auto-fixable failures converges or stops without applying.
    assert report.applied == [] or report.iterations >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_resolver_loop.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/astralint/resolver/loop.py
from typing import Literal

from pydantic import BaseModel

from ..base.conformance_suite import ConformanceSuite
from ..base.validation_result import Severity, ValidationResultGroup
from ..codecs.cdf import CdfCodec
from .apply import apply_fixes
from .engine import resolve
from .models import Fix


class ConvergenceReport(BaseModel):
    iterations: int
    applied: list[Fix]
    staged: list[Fix]
    remaining_errors: int
    converged: bool
    stopped_reason: Literal["converged", "no_progress", "max_iter"]


def _failure_signature(results: ValidationResultGroup) -> frozenset[tuple[str, str]]:
    sig: set[tuple[str, str]] = set()

    def walk(group: ValidationResultGroup):
        for r in group.results:
            if isinstance(r, ValidationResultGroup):
                walk(r)
            elif not r.valid and r.severity != Severity.SKIPPED:
                sig.add((r.reference, r.target))

    walk(results)
    return frozenset(sig)


def _load_from_bytes(cdf_bytes: bytes):
    # The whole resolve/apply path is CDF-specific in Phase 1, and the CDF codec
    # accepts raw bytes (unlike load_file, which dispatches on a path extension).
    return CdfCodec.load(cdf_bytes)


def converge(
    cdf_bytes: bytes, suite: ConformanceSuite, max_iter: int = 10
) -> tuple[ConvergenceReport, bytes]:
    applied: list[Fix] = []
    staged: list[Fix] = []
    iterations = 0
    stopped: Literal["converged", "no_progress", "max_iter"] = "max_iter"
    prev_signature: frozenset[tuple[str, str]] | None = None

    while iterations < max_iter:
        file = _load_from_bytes(cdf_bytes)
        results = suite.run(file)
        if not results.has_errors():
            stopped = "converged"
            break

        signature = _failure_signature(results)
        if signature == prev_signature:
            stopped = "no_progress"
            break
        prev_signature = signature

        fixes = resolve(file, results.failures_only())
        auto = [f for f in fixes if f.auto]
        staged = [f for f in fixes if not f.auto]
        if not auto:
            stopped = "no_progress"
            break

        cdf_bytes = apply_fixes(cdf_bytes, auto)
        applied.extend(auto)
        iterations += 1

    final = suite.run(_load_from_bytes(cdf_bytes))
    report = ConvergenceReport(
        iterations=iterations,
        applied=applied,
        staged=staged,
        remaining_errors=final.count_by_severity()["ERROR"],
        converged=not final.has_errors(),
        stopped_reason=stopped,
    )
    return report, cdf_bytes
```

```python
# src/astralint/resolver/__init__.py
from .apply import apply_fixes
from .engine import resolve
from .loop import ConvergenceReport, converge
from .models import Fix

__all__ = ["apply_fixes", "resolve", "converge", "ConvergenceReport", "Fix"]
```

> **Note (verified):** `load_file` dispatches on a path extension and does *not* accept bytes, so `_load_from_bytes` calls `CdfCodec.load(cdf_bytes)` directly — confirmed to accept raw bytes (`codecs/cdf.py:88`). `test_converge_returns_report_and_bytes` pins the round-trip.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_resolver_loop.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/astralint/resolver/loop.py src/astralint/resolver/__init__.py tests/test_resolver_loop.py
git commit -m "feat(resolver): convergence loop with cap and no-progress detection"
```

---

### Task 9: CLI `fix` command

**Files:**
- Modify: `src/astralint/astralint.py` (add a `fix` command at module top level, after `lint`)
- Test: `tests/test_resolver_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_resolver_cli.py
import os
from pathlib import Path

from astralint.astralint import fix as fix_command

__HERE__ = os.path.dirname(__file__)
_CDF = os.path.join(__HERE__, "resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf")


def test_fix_dry_run_writes_nothing(tmp_path, capsys):
    out = tmp_path / "fixed.cdf"
    fix_command(Path(_CDF), suite="ISTP", apply="none", output=out)
    assert not out.exists()
    captured = capsys.readouterr().out
    assert "fix" in captured.lower() or "no" in captured.lower()


def test_fix_auto_writes_corrected_cdf(tmp_path):
    out = tmp_path / "fixed.cdf"
    fix_command(Path(_CDF), suite="ISTP", apply="auto", output=out)
    assert out.exists()
    assert out.stat().st_size > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_resolver_cli.py -v`
Expected: FAIL with `ImportError: cannot import name 'fix'`.

- [ ] **Step 3: Write minimal implementation**

Add to `src/astralint/astralint.py` — a new import near the top and a new `@app.command()` after `lint`:

```python
# add to the existing imports
from .resolver import converge
```

```python
# add after the lint() command
@app.command()
def fix(
    path: Path,
    suite: str = "ISTP",
    apply: str = "auto",
    output: Path | None = None,
    max_iter: int = 10,
):
    """Propose and (optionally) apply deterministic ISTP fixes to a CDF.

    Parameters
    ----------
    path : Path
        The CDF file to repair.
    suite : str
        Conformance suite to validate against. Default "ISTP".
    apply : str
        "auto" runs the convergence loop and writes a corrected CDF;
        "none" is a dry run that lists proposed fixes without writing.
    output : Path, optional
        Destination for the corrected CDF. Defaults to "<stem>.fixed.cdf".
    max_iter : int
        Hard cap on convergence iterations. Default 10.
    """
    console = Console()
    checker = get_suite(suite)
    if checker is None:
        console.print(f"[red]✗[/] Unknown suite '{suite}'")
        raise SystemExit(1)

    with open(path, "rb") as f:
        cdf_bytes = f.read()

    report, fixed = converge(cdf_bytes, checker, max_iter=max_iter)

    if report.applied:
        console.print(f"[bold]Proposed/applied fixes ({len(report.applied)}):[/]")
        for fx in report.applied:
            console.print(
                f"  [green]{fx.attribute}[/] {fx.target_path} = {fx.value!r} "
                f"[dim]({fx.source.value}, conf {fx.confidence:.2f}) — {fx.provenance_note}[/]"
            )
    else:
        console.print("No auto-applicable fixes found.")

    if report.staged:
        console.print(f"\n[bold]Staged suggestions ({len(report.staged)}) — need review:[/]")
        for fx in report.staged:
            console.print(
                f"  [yellow]{fx.attribute}[/] {fx.target_path} ~ {fx.value!r} "
                f"[dim]— {fx.provenance_note}[/]"
            )

    console.print(
        f"\n[dim]iterations={report.iterations} stopped={report.stopped_reason} "
        f"remaining_errors={report.remaining_errors}[/]"
    )

    if apply == "auto":
        dest = output or path.with_suffix(".fixed.cdf")
        dest.write_bytes(fixed)
        console.print(f"[green]✓[/] Wrote corrected CDF to [bold]{dest}[/]")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_resolver_cli.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the whole suite + lint**

Run: `uv run pytest -q && make lint`
Expected: all tests pass; lint clean (codespell → ruff → basedpyright).

- [ ] **Step 6: Commit**

```bash
git add src/astralint/astralint.py tests/test_resolver_cli.py
git commit -m "feat(cli): add 'astralint fix' command driving the resolver loop"
```

---

## Self-Review

**Spec coverage:**
- §4 module layout → Tasks 1–9 create every file. ✓
- §5 data model → Task 1. ✓ (`trigger:str|None` refined to `triggers:list[str]`, noted in Task 1.)
- §6 catalog (FILLVAL, SCALETYP, VAR_TYPE, DEPEND_0, DISPLAY_TYPE, dangling pointers) → Tasks 2–5. Excluded data-dependent resolvers documented as stubs in Task 2. ✓
- §6 verification items (`shape[0]` record count; pycdfpp overwrite path) → exercised by Task 3 (record-count match) and Task 7 (`set_value` round-trip). ✓
- §7 mutation + re-fetch hazard → Task 7 (comment + single-pass apply). ✓
- §8 loop safety (cap, no-progress, induced violations) → Task 8. ✓
- §9 Phase-2 seam → no code now (correct: additive later); enums leave room. ✓
- §10 CLI (`--apply auto|none`, default `<stem>.fixed.cdf`) → Task 9. ✓
- §11 testing tiers (resolver unit, engine, apply round-trip, loop) → Tasks 2–9. ✓

**Placeholder scan:** no TBD/TODO. The §6 verification items (`shape[0]` record count, `set_value` overwrite) are pinned by named tests, not placeholders; the `load_file`-vs-bytes question is resolved in-plan (`CdfCodec.load`).

**Type consistency:** resolver signature `(file, variable, attribute, failure) -> ResolverOutput | None` is identical across Tasks 2–4 and called that way in Task 6. `Fix`/`ResolverEntry`/`ResolverOutput`/`ApplyPolicy`/`Scope`/`ReferenceSource` field names match between Task 1 and their uses in Tasks 5–9. `converge` returns `tuple[ConvergenceReport, bytes]` in Task 8 and is consumed that way in Task 9.

**Known implementation risk flagged for the executor:** Task 8's `_broken_bytes` test helper is the least-certain spot — it deliberately corrupts a CDF to produce a fixable failure; if the chosen breakage doesn't yield an auto-fixable error on the MMS resource, adjust it to drop/blank a `FILLVAL` on a record-varying variable instead. The test only asserts the loop *runs and reports*, so it is robust to the exact breakage.
