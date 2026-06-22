# PDS4 (CDF-A) conformance rules — design

**Date:** 2026-06-22
**Status:** approved, implementing first slice

## Context

PDS4, unlike PDS3, accepts CDF as an archival format. The authoritative spec is the
**"Guide to Archiving CDF Files in PDS4", Revision 7 (2018), Todd King & Joseph Mafi**
(a.k.a. the *CDF-A Specification*), published by NASA PDS / PDS-PPI:
<https://pds.nasa.gov/datastandards/documents/archiving/Guide-to-Archiving-CDF-Files-in-PDS4-v7.pdf>

It defines a PDS4-archivable CDF as an **ISTP/IACG-compliant CDF plus a small delta** of
structural and metadata constraints. AstraLint already validates CDF and reads it into the
`File` model, so the PDS4 suite is a thin profile over ISTP — the same pattern the `CDAWeb`
suite uses (`inherit_from: [ISTP]` + a `rules/` delta).

The previous `PDS4` stub (`rules/contiguous.yaml`) was copy-pasted ISTP/CDF concepts
(`variables/.*/attributes`, CATDESC/FIELDNAM/FILLVAL) that have nothing to do with PDS4. It
is removed.

## Requirements from the CDF-A spec

**Structural ("Requirements for Archivable CDF files"):**
1. CDF version ≥ 3.4
2. Single-file CDF (not multi-file)
3. **No compression — file or variable**
4. No fragmented variables (contiguous storage)
5. zVariables only (no rVariables)

**Metadata (CDF-A adds over ISTP/IACG):**
- `spase_DatasetResourceID` — **required** (ISTP only *recommends* it), format
  `spase://<naming_authority>/<unique_id>`
- `spase_DatasetResource`, `spase_GranuleResourceID`, `spase_GranuleResource` — optional

Everything else (Project, Discipline, Data_type, CATDESC, DEPEND_i, VAR_TYPE, …) is plain
ISTP, already validated and inherited.

## What is checkable against the current `File` model

The `File` model exposes `File.compression`, per-`Variable.compression`, and `attributes`,
but **not** CDF version, single-vs-multi-file, fragmentation, or zVariable-vs-rVariable.

| Rule (reference)                         | CDF-A source        | Severity | Checkable now |
| ---------------------------------------- | ------------------- | -------- | ------------- |
| `PDS4-CDFA-001` no file compression      | structural #3       | ERROR    | ✅ `compression == no_compression` |
| `PDS4-CDFA-002` no variable compression  | structural #3       | ERROR    | ✅ `variables/.*/compression` per var |
| `PDS4-GA-001` `spase_DatasetResourceID` present | CDF-A required | ERROR    | ✅ `contains_keys` on `attributes` |
| `PDS4-GA-002` `spase_DatasetResourceID` format  | CDF-A          | ERROR    | ✅ `matches ^spase://[^/]+/.+$` |
| `PDS4-GA-003` recommended SPASE attrs    | CDF-A optional      | INFO     | ✅ `contains_keys` (not required) |
| `PDS4-CDFA-003` CDF version ≥ 3.4        | structural #1       | ERROR    | ✅ `format_version` + `version_at_least` |
| contiguity / zVariables only             | structural #4,5     | —        | ❌ pycdfpp 0.10 doesn't expose it |
| single-file                              | structural #2       | —        | ✅ satisfied by construction (loader is single-file only) |

Compression surfaces as the pycdfpp `CompressionType` enum name — `no_compression` vs
`gzip_compression`/etc. — at the `File` root and on each `Variable`.

## Design

`PDS4` suite manifest gains `inherit_from: [ISTP]`. New `rules/` files (one rule per file,
mirroring ISTP layout):

- `Structural/NoFileCompression.yaml`        → `PDS4-CDFA-001` (ERROR)
- `Structural/NoVariableCompression.yaml`    → `PDS4-CDFA-002` (ERROR, per-variable)
- `Structural/CdfVersion.yaml`               → `PDS4-CDFA-003` (ERROR; `version_at_least` on `File.format_version`)
- `GlobalAttributes/SpaseDatasetResourceIdRequired.yaml` → `PDS4-GA-001` (ERROR)
- `GlobalAttributes/SpaseDatasetResourceIdFormat.yaml`   → `PDS4-GA-002` (ERROR)
- `GlobalAttributes/RecommendedSpaseAttributes.yaml`     → `PDS4-GA-003` (INFO)

All rule URLs point to the CDF-A guide. Messages carry both `{% if valid %}` and failure
branches (project convention since the readable-passing-rules work).

### Deliberate non-goals

- **No Epoch-name rule.** The CDF-A guide quotes ISTP's older "`DEPEND_0` must equal
  `'Epoch'` / Epoch first variable" text, but the ISTP suite was deliberately made
  name-agnostic (any CDF-time-typed variable is a valid epoch). We do not regress that.
- **No compression auto-fix.** Producing an uncompressed copy (pycdfpp re-save without
  compression) is a real future resolver entry but is out of scope here.
  `spase_DatasetResourceID` stays USER-only — never fabricated (identity/provenance).

## Structural constraints — resolution

After inspecting pycdfpp 0.10.0:

- **#1 version ≥ 3.4** — implemented. pycdfpp exposes `cdf.distribution_version` (a tuple);
  the codec formats it onto `File.format_version` ("3.5.0") and a new `version_at_least`
  assertion compares it numerically per component (so `3.10 > 3.9`, unlike a regex or string
  compare). Rule `PDS4-CDFA-003`.
- **#2 single-file** — satisfied by construction: AstraLint/pycdfpp only load single-file
  CDFs, so any validated file is single-file. No rule needed.
- **#4 contiguity / #5 zVariables** — pycdfpp does not surface the physical VVR layout or any
  r/z distinction. These need new bindings upstream in pycdfpp, then a per-`Variable` flag and
  `PDS4-CDFA-004/005`. Remaining backlog (issue #2).

## Testing

`tests/test_pds4_suite.py`, mirroring `test_cdaweb_suite.py`:
- PDS4 inherits every ISTP rule and adds the `PDS4-*` rules.
- A gzip-compressed file (the MMS resource CDF) fails `PDS4-CDFA-001`; an uncompressed
  synthetic `File` passes.
- A variable with compression fails `PDS4-CDFA-002`.
- A file without `spase_DatasetResourceID` fails `PDS4-GA-001`; a malformed value fails
  `PDS4-GA-002`; a well-formed `spase://…/…` passes both.
