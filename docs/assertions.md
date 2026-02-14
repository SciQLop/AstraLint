# AstraLint Assertions Reference

Assertions are the building blocks of validation rules. Each assertion checks a specific condition on the file model and returns a pass/fail result.

## Quick Reference

| Check | Category | Description |
|-------|----------|-------------|
| `exists` | Existence | Path exists in the file |
| `not_exists` | Existence | Path does NOT exist |
| `comparison` | Value | Compare with `=`, `!=`, `<`, `<=`, `>`, `>=` |
| `range` | Value | Value is within numeric range |
| `is_type` | Value | Data type matches (CHAR, FLOAT32, TT2000, etc.) |
| `matches` | String | String matches regex pattern |
| `contains_keys` | Collection | Object has all required keys |
| `in` | Collection | Value is contained in another |
| `not_in` | Collection | Value is NOT contained |
| `length` | Collection | Length check (exact, min, max) |
| `not_empty` | Collection | Length > 0 |
| `requires` | Collection | Object contains required key |
| `array_shape` | Collection | Array matches dimensions |
| `reference_variable` | Relationship | Value references existing variable |
| `all_of` | Combinator | All nested assertions pass |
| `any_of` | Combinator | At least one passes |
| `not` | Combinator | Nested assertions must fail |

---

## Existence Checks

### `exists`

Checks that a path exists in the file.

```yaml
- path: "variables/.*/attributes/CATDESC"
  check: exists
  message: "Variable missing CATDESC attribute"
```

### `not_exists`

Checks that a path does NOT exist (useful for deprecated attributes).

```yaml
- path: "attributes/DEPRECATED_ATTR"
  check: not_exists
  message: "Deprecated attribute should not be present"
```

---

## Value Comparisons

### `comparison`

Compare a value using standard operators.

**Operators:** `=`, `!=`, `<`, `<=`, `>`, `>=`

```yaml
# Check VALIDMIN is non-negative
- path: "variables/.*/attributes/VALIDMIN"
  check: comparison
  operator: ">="
  value: 0
  message: "VALIDMIN must be non-negative"

# Check version equals expected
- path: "attributes/Data_version"
  check: comparison
  operator: "="
  value: "1.0"
  message: "Data version must be 1.0"
```

### `range`

Check that a numeric value falls within a range (inclusive).

```yaml
- path: "variables/.*/attributes/SCALE_MIN"
  check: range
  min: -1000
  max: 1000
  message: "SCALE_MIN out of acceptable range [-1000, 1000]"
```

### `is_type`

Check the data type of a value or variable.

**Available types:** `CHAR`, `UINT8`, `UINT16`, `UINT32`, `UINT64`, `INT8`, `INT16`, `INT32`, `INT64`, `FLOAT32`, `FLOAT64`, `TT2000`, `CDFEPOCH`, `CDFEPOCH16`

```yaml
# Epoch variable should use TT2000
- path: "variables/Epoch/data_type"
  check: is_type
  type: TT2000
  message: "Epoch variable should use TT2000 data type"

# Check all variables' data types
- path: "variables/.*/data_type"
  check: is_type
  type: FLOAT64
  message: "Data variables should use FLOAT64"

# Check first data type of an attribute (data_type is now a list)
- path: "attributes/Project/data_type/0"
  check: is_type
  type: CHAR
  message: "Project attribute must be a string"
```

---

## String Matching

### `matches`

Validate that a string matches a regular expression pattern.

```yaml
# Check Logical_source follows naming convention
- path: "attributes/Logical_source"
  check: matches
  pattern: "^[a-z0-9]+_[a-z0-9]+_[a-z0-9]+$"
  message: "Logical_source must follow format: source_datatype_descriptor"

# Check FIELDNAM starts with a letter
- path: "variables/.*/attributes/FIELDNAM"
  check: matches
  pattern: "^[A-Za-z].*"
  message: "FIELDNAM must start with a letter"
```

---

## Collection Checks

### `contains_keys`

Check that an object (dict) contains all specified keys.

```yaml
# Mandatory global attributes
- path: "attributes"
  check: contains_keys
  keys:
    - Project
    - Source_name
    - Discipline
    - Data_type
    - Logical_source
  message: "Missing mandatory global attributes"
```

### `in`

Check that a value is contained within another value (list membership or substring).

```yaml
# VAR_TYPE must be one of allowed values
- path: "variables/.*/attributes/VAR_TYPE"
  check: in
  value: ["data", "support_data", "metadata", "ignore_data"]
  message: "VAR_TYPE must be: data, support_data, metadata, or ignore_data"
```

### `not_in`

Check that a value is NOT contained (forbidden values).

```yaml
# DISPLAY_TYPE cannot be deprecated values
- path: "variables/.*/attributes/DISPLAY_TYPE"
  check: not_in
  value: ["deprecated_stack", "old_spectrogram"]
  message: "DISPLAY_TYPE uses deprecated value"
```

### `length`

Check the length of a string, list, or other sized object.

**Parameters:** Use `value` for exact length, or `min`/`max` for range.

```yaml
# Exact length
- path: "attributes/Data_version"
  check: length
  value: 3
  message: "Data_version must be exactly 3 characters (e.g., '1.0')"

# Length range
- path: "variables/.*/attributes/CATDESC"
  check: length
  min: 1
  max: 80
  message: "CATDESC should be 1-80 characters"

# Minimum only
- path: "attributes/TEXT"
  check: length
  min: 10
  message: "TEXT attribute too short"
```

### `not_empty`

Shorthand for checking that a value has length > 0.

```yaml
- path: "variables/.*/attributes/FIELDNAM"
  check: not_empty
  message: "FIELDNAM cannot be empty"
```

### `requires`

Check that an object contains a specific key (similar to `contains_keys` but for a single key).

```yaml
- path: "variables/.*/attributes"
  check: requires
  key: "VAR_TYPE"
  message: "All variables must have VAR_TYPE attribute"
```

### `array_shape`

Check that an array matches expected dimensions.

```yaml
- path: "variables/vector_data/shape"
  check: array_shape
  shape: [3, 100]
  message: "Vector data must have shape [3, 100]"
```

---

## Relationship Checks

### `reference_variable`

Check that a value references an existing variable name in the file.

```yaml
# DEPEND_0 must point to a real variable
- path: "variables/.*/attributes/DEPEND_0"
  check: reference_variable
  message: "DEPEND_0 must reference an existing variable"

# LABL_PTR_1 must reference a label variable
- path: "variables/.*/attributes/LABL_PTR_1"
  check: reference_variable
  message: "LABL_PTR_1 must reference an existing variable"
```

---

## Logical Combinators

Combinators allow you to build complex validation logic from simple assertions.

### `all_of`

All nested assertions must pass.

```yaml
# VALIDMIN and VALIDMAX must both exist
- path: "variables/.*/attributes"
  check: all_of
  message: "VALIDMIN and VALIDMAX must both be present"
  assertions:
    - path: "VALIDMIN"
      check: exists
      message: ""
    - path: "VALIDMAX"
      check: exists
      message: ""
```

### `any_of`

At least one nested assertion must pass.

```yaml
# Variable must have either DEPEND_0 or DEPEND_TIME
- path: "variables/.*/attributes"
  check: any_of
  message: "Variable must have either DEPEND_0 or DEPEND_TIME"
  assertions:
    - path: "DEPEND_0"
      check: exists
      message: ""
    - path: "DEPEND_TIME"
      check: exists
      message: ""
```

### `not`

Nested assertions must NOT pass (negation).

```yaml
# Ensure variable is NOT using deprecated type
- path: "variables/.*"
  check: not
  message: "Variable should not use FLOAT32 type for this data"
  assertions:
    - path: "config/data_type"
      check: is_type
      type: FLOAT32
      message: ""
```

---

## Complete Rule Example

Here's a complete YAML rule file showing multiple assertions:

```yaml
name: ISTP_DataVariables
description: "Validation rules for ISTP data variables"
url: "https://spdf.gsfc.nasa.gov/istp_guide/variables.html"
reference: "ISTP-VAR-001"
severity: ERROR
suite: ISTP

assertions:
  # CATDESC is mandatory and must be non-empty
  - path: "variables/.*/attributes/CATDESC"
    check: exists
    message: "Variable missing CATDESC attribute"

  - path: "variables/.*/attributes/CATDESC"
    check: not_empty
    message: "CATDESC cannot be empty"

  - path: "variables/.*/attributes/CATDESC"
    check: length
    max: 80
    message: "CATDESC exceeds 80 character limit"

  # VAR_TYPE must be valid
  - path: "variables/.*/attributes/VAR_TYPE"
    check: in
    values: ["data", "support_data", "metadata", "ignore_data"]
    message: "Invalid VAR_TYPE value"

  # DEPEND_0 must reference existing variable
  - path: "variables/.*/attributes/DEPEND_0"
    check: reference_variable
    message: "DEPEND_0 references non-existent variable"
```

---

## Path Patterns

Assertions use `/`-separated paths with regex support to target values in the file model.

### Basic Paths

| Pattern | Matches |
|---------|---------|
| `attributes` | Global attributes dictionary |
| `attributes/Project` | Specific global attribute |
| `variables` | All variables dictionary |
| `variables/Epoch` | Specific variable by name |
| `variables/.*` | All variables (regex) |
| `variables/.*/attributes` | Attributes of all variables |
| `variables/.*/attributes/CATDESC` | CATDESC attribute on all variables |
| `variables/Epoch/data_type` | Data type of specific variable |
| `variables/.*/data_type` | Data type of all variables |

### Accessing List Elements

Lists are indexed using numeric paths (0-based):

| Pattern | Matches |
|---------|---------|
| `variables/Epoch/shape/0` | First dimension of Epoch's shape |
| `variables/Epoch/shape/1` | Second dimension |
| `variables/.*/shape/0` | First dimension of all variables |
| `attributes/Project/data_type/0` | First data type of Project attribute |
| `attributes/.*/data_type/.*` | All data types of all attributes |

**Examples:**

```yaml
# Check first dimension of variable shape is > 0
- path: "variables/.*/shape/0"
  check: comparison
  operator: ">"
  value: 0
  message: "First dimension must be positive"

# Check attribute has at least one data type entry
- path: "attributes/.*/data_type/0"
  check: exists
  message: "Attribute must have at least one data type"

# Match any element in shape array using regex
- path: "variables/Epoch/shape/[0-9]+"
  check: comparison
  operator: ">"
  value: 0
  message: "All dimensions must be positive"
```

### Regex Support

The path system uses Python's `re.fullmatch()`, so regex patterns work:

| Pattern | Description |
|---------|-------------|
| `.*` | Match any single path segment |
| `[A-Z]+` | Match uppercase letters only |
| `data_.*` | Match paths starting with "data_" |
| `[0-9]+` | Match any numeric index |
| `(Epoch\|Time)` | Match "Epoch" or "Time" |


