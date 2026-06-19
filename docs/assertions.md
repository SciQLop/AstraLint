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
| `compare_to` | Relationship | Compare values at two different paths |
| `all_of` | Combinator | All nested assertions pass (AND) |
| `any_of` | Combinator | At least one passes (OR) |
| `none_of` | Combinator | None must pass (NOR) |
| `not` | Combinator | Nested assertion must fail (NOT) |
| `one_of` | Combinator | Exactly one must pass (XOR) |
| `if_then` | Conditional | If condition passes, then assertion must pass |
| `if_then_else` | Conditional | If-then with else branch |
| `at_least` | Counting | At least N assertions must pass |
| `at_most` | Counting | At most N assertions can pass |
| `exactly` | Counting | Exactly N assertions must pass |

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

### `compare_to`

Compare a value at one path against a value at another path in the same file. Supports named path captures for cross-variable comparisons.

**Operators:** `=`, `!=`, `<`, `<=`, `>`, `>=`

```yaml
# FILLVAL must be less than VALIDMIN (same variable)
- path: "variables/{var}/attributes/FILLVAL/values/0"
  check: compare_to
  operator: "<"
  other_path: "variables/{var}/attributes/VALIDMIN/values/0"
  message: "Variable '{{ var }}': FILLVAL must be less than VALIDMIN"
```

```yaml
# Compare attribute entry counts
- path: "attributes/HTTP_LINK/shape/0"
  check: compare_to
  operator: "="
  other_path: "attributes/LINK_TEXT/shape/0"
  message: "HTTP_LINK and LINK_TEXT must have the same number of entries"
```

---

## Logical Combinators

Combinators allow you to build complex validation logic from simple assertions.

### `all_of`

All nested assertions must pass (logical AND).

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

At least one nested assertion must pass (logical OR).

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

### `none_of`

None of the nested assertions must pass (logical NOR). Useful for ensuring forbidden conditions are not met.

```yaml
# Variable must not have any deprecated attributes
- check: none_of
  assertions:
    - path: "variables/.*/attributes/OLD_ATTR"
      check: exists
    - path: "variables/.*/attributes/DEPRECATED"
      check: exists
```

### `not`

The nested assertion must NOT pass (logical NOT / negation).

```yaml
# Ensure variable is NOT using deprecated type
- check: not
  assertion:
    path: "variables/data/data_type"
    check: is_type
    type: FLOAT32
```

### `one_of`

Exactly one nested assertion must pass (logical XOR). Useful for mutually exclusive conditions.

```yaml
# Variable must be exactly one type: data OR support_data
- check: one_of
  assertions:
    - path: "variables/var1/attributes/VAR_TYPE"
      check: comparison
      operator: "="
      value: "data"
    - path: "variables/var1/attributes/VAR_TYPE"
      check: comparison
      operator: "="
      value: "support_data"
```

---

## Conditional Assertions

Conditional assertions allow you to run checks only when certain conditions are met.

### `if_then`

If the condition passes, then the assertion must pass. If the condition fails, the assertion is **skipped** (considered valid with `SKIPPED` severity).

This implements logical implication: `condition → assertion`

```yaml
# If variable has DEPEND_0, then DEPEND_0 must reference an existing variable
- check: if_then
  if:
    path: "variables/data/attributes/DEPEND_0"
    check: exists
  then:
    path: "variables/data/attributes/DEPEND_0"
    check: reference_variable
```

```yaml
# If using TT2000, then VALIDMIN must be positive
- check: if_then
  if:
    path: "variables/Epoch/data_type"
    check: is_type
    type: TT2000
  then:
    path: "variables/Epoch/attributes/VALIDMIN"
    check: comparison
    operator: ">"
    value: 0
```

**Skipped Behavior:**
- When the `if` condition fails, the result is `valid=True` with `severity=SKIPPED`
- Skipped assertions are treated as passing in parent combinators like `all_of`
- This allows conditional rules that don't fail when the condition doesn't apply

**Per-variable conditionals (path captures):**

When the `if` path contains a named capture like `{var}`, the condition and the
`then`/`else` branches are evaluated **once per matched binding**, with the
capture interpolated into every path (and message) of the branch. This correlates
the condition and the requirement on the *same* variable — without it, a wildcard
condition such as `variables/.*/.../VAR_TYPE == "data"` would only be satisfied
when *every* variable shares that type, silently skipping mixed-type files.

```yaml
# For each variable whose VAR_TYPE is "data", require DEPEND_0 on that variable.
- check: if_then
  if:
    path: "variables/{var}/attributes/VAR_TYPE/values/0"
    check: comparison
    operator: "="
    value: "data"
  then:
    path: "variables/{var}/attributes"
    check: contains_keys
    keys: [DEPEND_0]
```

### `if_then_else`

If the condition passes, run the `then` branch; otherwise, run the `else` branch. Unlike `if_then`, this always runs one of the two branches (never skipped).

```yaml
# If TT2000, check nanosecond precision; otherwise check regular precision
- check: if_then_else
  if:
    path: "variables/Epoch/data_type"
    check: is_type
    type: TT2000
  then:
    path: "variables/Epoch/attributes/TIME_SCALE"
    check: comparison
    operator: "="
    value: "UTC"
  else:
    path: "variables/Epoch/attributes/TIME_SCALE"
    check: comparison
    operator: "="
    value: "TAI"
```

```yaml
# Different validation based on variable type
- check: if_then_else
  if:
    path: "variables/var1/attributes/VAR_TYPE"
    check: comparison
    operator: "="
    value: "data"
  then:
    # Data variables need CATDESC
    path: "variables/var1/attributes/CATDESC"
    check: exists
  else:
    # Support variables need FIELDNAM
    path: "variables/var1/attributes/FIELDNAM"
    check: exists
```

---

## Counting Assertions

Counting assertions check how many of the nested assertions pass.

### `at_least`

At least N assertions must pass.

```yaml
# At least 2 of these attributes must be present
- check: at_least
  count: 2
  assertions:
    - path: "attributes/Project"
      check: exists
    - path: "attributes/Source_name"
      check: exists
    - path: "attributes/Discipline"
      check: exists
```

### `at_most`

At most N assertions can pass. Useful for limiting optional attributes.

```yaml
# At most 1 deprecated attribute is allowed
- check: at_most
  count: 1
  assertions:
    - path: "attributes/OLD_PROJECT"
      check: exists
    - path: "attributes/LEGACY_SOURCE"
      check: exists
    - path: "attributes/DEPRECATED_FLAG"
      check: exists
```

### `exactly`

Exactly N assertions must pass. Useful for mutually exclusive options where you need exactly N.

```yaml
# Exactly 2 of these 4 coordinate attributes must be present
- check: exactly
  count: 2
  assertions:
    - path: "attributes/COORD_X"
      check: exists
    - path: "attributes/COORD_Y"
      check: exists
    - path: "attributes/COORD_Z"
      check: exists
    - path: "attributes/COORD_R"
      check: exists
```

---

## Validation Results and Severity Levels

Each assertion returns a validation result with a `valid` flag and a `severity` level.

### Severity Levels

| Severity | Description |
|----------|-------------|
| `ERROR` | Mandatory requirement not met. The file fails validation. |
| `WARNING` | Recommended practice not followed. The file passes but with warnings. |
| `INFO` | Informational message. The assertion passed successfully. |
| `SKIPPED` | Condition not met, assertion was not evaluated (used by `if_then`). |

### Skipped Results

The `SKIPPED` severity is used by conditional assertions (like `if_then`) when the condition is not met. Skipped results:

- Are considered **valid** (`valid=True`)
- Do not count as failures in combinators like `all_of`
- Are tracked separately in result counts
- Allow conditional rules that don't fail when the condition doesn't apply

**Example:**

```yaml
# This rule is skipped if the variable doesn't exist
- check: if_then
  if:
    path: "variables/optional_var"
    check: exists
  then:
    path: "variables/optional_var/data_type"
    check: is_type
    type: FLOAT64
```

If `optional_var` doesn't exist, the result is:
- `valid: True`
- `severity: SKIPPED`
- `message: "Condition not met, assertion skipped."`

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

### Advanced Example with Conditional and Counting Assertions

```yaml
name: Advanced_Validation
description: "Advanced validation with conditionals and counting"
url: "https://example.com/docs"
reference: "ADV-001"
severity: ERROR
suite: CUSTOM

assertions:
  # All variables must satisfy multiple conditions
  - check: all_of
    assertions:
      # Variable must exist
      - path: "variables/data_var"
        check: exists
      
      # If variable has DEPEND_0, it must reference a valid variable
      - check: if_then
        if:
          path: "variables/data_var/attributes/DEPEND_0"
          check: exists
        then:
          path: "variables/data_var/attributes/DEPEND_0"
          check: reference_variable
      
      # At least 2 of these recommended attributes should be present
      - check: at_least
        count: 2
        assertions:
          - path: "variables/data_var/attributes/CATDESC"
            check: exists
          - path: "variables/data_var/attributes/FIELDNAM"
            check: exists
          - path: "variables/data_var/attributes/UNITS"
            check: exists
      
      # Variable type must be exactly one of data or support_data
      - check: one_of
        assertions:
          - path: "variables/data_var/attributes/VAR_TYPE"
            check: comparison
            operator: "="
            value: "data"
          - path: "variables/data_var/attributes/VAR_TYPE"
            check: comparison
            operator: "="
            value: "support_data"
  
  # Different validation based on data type
  - check: if_then_else
    if:
      path: "variables/Epoch/data_type"
      check: is_type
      type: TT2000
    then:
      # TT2000 requires specific time attributes
      check: all_of
      assertions:
        - path: "variables/Epoch/attributes/TIME_BASE"
          check: exists
        - path: "variables/Epoch/attributes/TIME_SCALE"
          check: comparison
          operator: "="
          value: "UTC"
    else:
      # Non-TT2000 epoch just needs basic attributes
      path: "variables/Epoch/attributes/VALIDMIN"
      check: exists
  
  # No deprecated attributes should be present
  - check: none_of
    assertions:
      - path: "attributes/DEPRECATED_ATTR"
        check: exists
      - path: "attributes/OLD_FORMAT"
        check: exists
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

### Named Captures

Capture path segments for reuse in `other_path` and `message` fields using `{name}` syntax:

| Syntax | Description |
|--------|-------------|
| `{name}` | Capture segment, matches any single path component |
| `{name:pattern}` | Capture segment with custom regex pattern |

Captured names can be used in:
- `other_path` — to reference the same captured value in a different location
- `message` — as Jinja2 variables (e.g. `{{ var }}`), available in all assertion types

```yaml
# Capture variable name, reuse in other_path and message
- path: "variables/{var}/attributes/FILLVAL/values/0"
  check: compare_to
  operator: "<"
  other_path: "variables/{var}/attributes/VALIDMIN/values/0"
  message: "Variable '{{ var }}': FILLVAL must be less than VALIDMIN"

# Capture with custom regex filter
- path: "variables/{var:LFR_.*}/attributes/UNITS/values/0"
  check: not_empty
  message: "LFR variable '{{ var }}' must have non-empty UNITS"
```


