# Resolver Fixability Roadmap — ISTP coverage map

**Status:** roadmap (living). Phase 1 (PR #25) shipped the deterministic foundation; this maps every ISTP rule to how a fix can be produced, defining the path toward proposing a disposition for *almost every* error.

**Disposition legend:** **AUTO** = deterministic, safe to auto-apply · **STAGED** = computable but needs a human OK (lossy/ambiguous/partial) · **DATA** = needs variable data arrays (the File model is metadata-only today) · **USER** = irreducibly human (external IDs, prose, controlled vocabulary). ✅ = shipped in PR #25.

## Principle

Every error should get *a disposition* — AUTO, STAGED, or USER ("needs your input") — so nothing is silently unaddressable, even when the value can't be computed. The "fix hint" in `lint` follows coverage and reports honest auto / staged / user counts.

## Global attributes

| Rule | Sev | Attribute | Class | Disposition |
|---|---|---|---|---|
| GA-004 LogicalFileIdFormat | E | Logical_file_id | filename | **AUTO** (= filename stem; regex `^[a-z0-9_-]+_\d{8}(_v\d+)?$`) |
| GA-003 LogicalSourceFormat | E | Logical_source | filename | **AUTO** (= stem minus `_YYYYMMDD[_vN]`; regex `source_descriptor_datatype`) |
| GA-005 DataVersionFormat | E | Data_version | filename | **AUTO** (from `_vNN` → numeric `^\d+(\.\d+)*$`) |
| GA-008 DescriptorFormat | E | Descriptor | filename+prose | **STAGED** (abbrev from filename; `>Full description` is human — regex `ABBREV>.+`) |
| GA-006 DataTypeFormat | E | Data_type | filename+prose | **STAGED** (same `ABBREV>.+` shape) |
| GA-007 SourceNameFormat | E | Source_name | filename+prose | **STAGED** (mission abbrev from filename; full name human) |
| GA-015 GenerationDateFormat | W | Generation_date | date | **AUTO** (reformat existing value to `yyyymmdd`, else today) |
| GA-001 MandatoryGlobalAttributes | E | (set) | mixed | AUTO/STAGED for the filename ones above; **USER** for PI_name, PI_affiliation, TEXT, Project, Acknowledgement, Mission_group |
| GA-013 LinkCountConsistency | E | HTTP_LINK/LINK_* | consistency | STAGED (counts must match; which links is intent) |
| GA-002 RecommendedGlobalAttributes | W | DOI, spase_ID, Time_resolution | user/data | USER (DOI/spase); DATA (Time_resolution from epoch cadence) |
| GA-009/010/016 Discipline/Instrument_type/Mission_group | W | controlled vocab | enum | USER (offer closest-in-set suggestion) |
| GA-011/012/014 TEXT/Project/DOI | E/W | prose / ID | user | USER |

## Variable attributes

| Rule | Sev | Attribute | Class | Disposition |
|---|---|---|---|---|
| VA-013 ScaleTypValues | W | SCALETYP | type | ✅ AUTO |
| VA-004 VarTypeValues | E | VAR_TYPE | graph | ✅ AUTO |
| VA-005 DisplayTypeValues | W | DISPLAY_TYPE | graph | ✅ AUTO |
| VA-011/012/014/016/017/018 *PtrReferences | E | DEPEND/LABL/DELTA/UNIT/FORM/SCAL_PTR | reference | ✅ STAGED |
| VA-001/002/003/015 Mandatory/Data/Support/Metadata attrs | E | VAR_TYPE, DEPEND_0, FILLVAL, … | graph+type | ✅ partial (graph/type subset); USER for UNITS/CATDESC/FIELDNAM |
| VA-019 FillvalOutsideRange | E | FILLVAL vs VALIDMIN/MAX | type | AUTO (set standard ISTP fill, which is out of range) |
| VA-022 LablaxisMaxLength | E | LABLAXIS | truncate | STAGED (lossy) |
| VA-020 CatdescMaxLength | E | CATDESC | truncate | STAGED |
| VA-021 FieldnamMaxLength | E | FIELDNAM | truncate | STAGED |
| VA-008 LablaxisLength | W | LABLAXIS | truncate | STAGED |
| VA-010 FormatSpecifier | W | FORMAT | data | DATA (from type + observed magnitude) |
| VA-009 UnitsNotEmpty | E | UNITS | physical | USER (never fabricate units) |
| VA-006/007 Catdesc/Fieldnam length | W | CATDESC/FIELDNAM | prose | USER |

## Variables

| Rule | Sev | Class | Disposition |
|---|---|---|---|
| VAR-002 EpochAttributes (VAR_TYPE=support_data) | E | graph | **AUTO** — resolver exists; just wire the trigger |
| VAR-003 EpochRecommendedAttributes (MONOTON, TIME_BASE) | W | data+type | DATA (MONOTON); AUTO (TIME_BASE default) |
| VAR-001 EpochVariable (≥1 time var) | E | structural | USER (can't fabricate a time axis) |

## Phase-1b priority order

1. **Filename-derived globals — AUTO subset** (GA-004 Logical_file_id, GA-003 Logical_source, GA-005 Data_version) + a new `filename` ReferenceSource and an ISTP-filename parser. Highest real-world value (the common CDAWeb / mission non-compliance). *This is the slice being built now.*
2. **Filename globals — STAGED subset** (GA-008/006/007 Descriptor/Data_type/Source_name): propose the `ABBREV>` skeleton from the filename, flag the description for the human.
3. **Free graph wins**: wire VAR-002 and the VA-001 VAR_TYPE path into the existing graph resolvers (few registry lines).
4. **Generation_date** (GA-015) + **FillvalOutsideRange** (VA-019) — small deterministic resolvers.
5. **Truncation set** (VA-008/020/021/022) — one staged resolver.
6. **DATA tier** (FORMAT, MONOTON, Time_resolution) — requires extending the codec/File model to carry variable data; separate, larger milestone.
7. **USER-flagging**: give the irreducible rules a "needs your input" disposition so the `lint` fix-hint can show honest auto/staged/user counts.
