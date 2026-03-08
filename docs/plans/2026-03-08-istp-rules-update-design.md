# ISTP Rules Update Design

## Goal

Update the ISTP conformance suite to accurately reflect the ISTP Metadata Guidelines specification. Fix incorrect severities, wrong values, missing rules, and extend the assertion system where needed.

## Approach

Fix-in-place: edit existing YAML rules, add new ones, extend assertions minimally. Keep current file organization (GlobalAttributes/, VariableAttributes/, Variables/).

## 1. Assertion System Extensions

### 1a. Path Captures

Add a capture mechanism to paths using `{name}` syntax (inspired by FastAPI/OpenAPI):

- `{var}` — capture into `var`, matches `.*` (default)
- `{var:LFR_.*}` — capture with custom regex pattern
- Plain `.*` still works (anonymous, no capture)

Captured values can be substituted in:
- `other_path` fields (for `compare_to`)
- `message` strings (for better error reporting)

### 1b. `compare_to` Assertion

Compare a value at the matched path against a value at another path in the same file.

```yaml
- path: "variables/{var}/attributes/FILLVAL/values/0"
  check: compare_to
  operator: "<"
  other_path: "variables/{var}/attributes/VALIDMIN/values/0"
  message: "Variable '{var}': FILLVAL must be less than VALIDMIN"
```

Operators: `=`, `!=`, `<`, `<=`, `>`, `>=`. Absolute paths with capture substitution.

## 2. Fixes to Existing Rules

### Global Attributes

| Rule | Change |
|------|--------|
| MandatoryGlobalAttributes (GA-001) | Remove `Discipline`, `Project` (they are recommended, not required) |
| RecommendedGlobalAttributes (GA-002) | Add `Discipline`, `Project`, `DOI`, `spase_DatasetResourceID` |
| DisciplineValues (GA-009) | Replace with 5 spec values (remove Planetary Physics entries, add Astrophysics Science) |
| InstrumentTypeValues (GA-010) | Replace with all 17 spec values |

### Variable Attributes

| Rule | Change |
|------|--------|
| DataVariableAttributes (VA-002) | `LABLAXIS` becomes `any_of(LABLAXIS, LABL_PTR_1)`; `UNITS` becomes `any_of(UNITS, UNIT_PTR)` |
| SupportDataVariableAttributes (VA-003) | Add `LABLAXIS`/`LABL_PTR_i`; conditional `DEPEND_0` if RV; `FORMAT` becomes `any_of(FORMAT, FORM_PTR)`; `FILLVAL` conditional on RV |
| MandatoryVariableAttributes (VA-001) | `FILLVAL` conditional on `record_variance = true` |
| CatdescLength (VA-006) | WARNING at 80 (preferred), ERROR at 120 (hard max) |
| FieldnamLength (VA-007) | WARNING at 30 (preferred), ERROR at 50 (hard max) |
| LablaxisLength (VA-008) | WARNING at 10 (preferred), ERROR at 20 (hard max) |

### Variables

| Rule | Change |
|------|--------|
| EpochVariable (VAR-001) | Keep `Epoch` check as WARNING; add check that at least one var is referenced via DEPEND_0 |
| EpochAttributes (VAR-002) | `MONOTON`, `TIME_BASE`, `TIME_SCALE` become WARNING (recommended) |

## 3. New Rules

### Variable Attributes

| Rule | Severity | Description |
|------|----------|-------------|
| MetadataVariableAttributes (VA-015) | ERROR | If `VAR_TYPE = "metadata"`: require CATDESC, FIELDNAM, FORMAT/FORM_PTR. Conditional DEPEND_0/FILLVAL if RV |
| UnitPtrReferences (VA-016) | ERROR | UNIT_PTR must reference existing variable |
| FormPtrReferences (VA-017) | ERROR | FORM_PTR must reference existing variable |
| ScalPtrReferences (VA-018) | ERROR | SCAL_PTR must reference existing variable |
| FillvalOutsideRange (VA-019) | ERROR | FILLVAL < VALIDMIN or FILLVAL > VALIDMAX (uses `compare_to`) |

### Global Attributes

| Rule | Severity | Description |
|------|----------|-------------|
| LinkCountConsistency (GA-013) | ERROR | HTTP_LINK, LINK_TEXT, LINK_TITLE must have same number of entries |
| DOIFormat (GA-014) | WARNING | If DOI exists, must match `^https://doi\.org/.+/.+$` |
| GenerationDateFormat (GA-015) | WARNING | If Generation_date exists, must match `^\d{8}$` |

### Informational (PROPOSAL attributes)

| Rule | Severity | Description |
|------|----------|-------------|
| ProposalAttributes (INFO-001) | INFO | Check for COORDINATE_SYSTEM, DELTA_MINUS, DELTA_PLUS, Data_processing_level, FRAME_ORIGIN, FRAME_VELOCITY |

## 4. Severity Philosophy

- **ERROR**: Spec says "required" or "must"
- **WARNING**: Spec says "recommended", "should", or "preferred" limits
- **INFO**: PROPOSAL attributes, purely informational

For length limits with both preferred and hard max: WARNING at preferred, ERROR at hard max.

## 5. Documentation

- Update `docs/assertions.md` with `compare_to` assertion and path capture syntax
- Update tests for all changed and new rules
- Update tests for new assertion type and capture mechanism
