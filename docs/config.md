# AstraLint Configuration

AstraLint supports flexible configuration through multiple sources, allowing you to customize linting behavior at the project level.

## Configuration Sources

Configuration is loaded and merged from the following sources (highest to lowest priority):

| Priority | Source | Description |
|----------|--------|-------------|
| 1 (highest) | CLI arguments | `--suite`, `--select`, `--ignore`, etc. |
| 2 | `.astralint.yaml` | Project-level YAML config file |
| 3 | `pyproject.toml` | `[tool.astralint]` section |
| 4 (lowest) | Built-in defaults | Sensible defaults for all options |

Higher priority sources override lower ones. Nested options (like `output`) are deep-merged.

## Quick Start

```bash
# Generate a starter config file
astralint config init

# Validate your config file for errors
astralint config validate

# Show the resolved configuration (merged from all sources)
astralint config show

# Lint with verbose output (shows which config is used)
astralint lint myfile.cdf --verbose
```

## Config File Locations

AstraLint auto-detects configuration files in your project root (directory containing `pyproject.toml` or `.git`):

- `.astralint.yaml` (preferred)
- `.astralint.yml`
- `astralint.yaml`
- `astralint.yml`

You can also specify an explicit config file:

```bash
astralint lint myfile.cdf --config-file ./custom-config.yaml
```

---

## Configuration Options

### `suite`

**Type:** `string`  
**Default:** `"ISTP"`

The conformance suite to use for validation.

```yaml
suite: ISTP
```

```toml
[tool.astralint]
suite = "PDS4"
```

**Available suites:**
- `ISTP` - NASA ISTP Metadata Guidelines
- `PDS4` - Planetary Data System v4

---

### `select`

**Type:** `list[string]`  
**Default:** `[]` (all rules)

List of rule patterns to include. Supports regex patterns. When specified, only matching rules are run.

```yaml
select:
  - "MandatoryGlobalAttributes"
  - "ISTP-VAR-.*"          # All rules starting with ISTP-VAR-
  - ".*Attributes"          # Any rule ending with "Attributes"
```

```toml
[tool.astralint]
select = ["MandatoryGlobalAttributes", "ISTP-VAR-.*"]
```

Rules can be matched by:
- **Name:** `MandatoryGlobalAttributes`
- **Reference ID:** `ISTP-MD-003`
- **Regex pattern:** `ISTP-.*`, `.*Attributes`

---

### `ignore`

**Type:** `list[string]`  
**Default:** `[]` (ignore none)

List of rule patterns to exclude. Supports regex patterns. Cannot be used together with `select`.

```yaml
ignore:
  - "DeprecatedRule"
  - "ISTP-MD-00[0-9]"      # Ignore ISTP-MD-001 through ISTP-MD-009
```

```toml
[tool.astralint]
ignore = ["DeprecatedRule", "ISTP-MD-00[0-9]"]
```

---

### `severity_overrides`

**Type:** `dict[string, string]`  
**Default:** `{}`

Override the severity level of specific rules. Useful for demoting errors to warnings during migration.

```yaml
severity_overrides:
  ISTP-VAR-001: WARNING    # Demote to warning
  ISTP-MD-003: INFO        # Demote to info
```

```toml
[tool.astralint.severity_overrides]
"ISTP-VAR-001" = "WARNING"
"ISTP-MD-003" = "INFO"
```

**Valid severities:** `ERROR`, `WARNING`, `INFO`

---

### `extra_rules`

**Type:** `list[path]`  
**Default:** `[]`

Additional directories containing custom YAML rule definitions.

```yaml
extra_rules:
  - "./custom_rules/"
  - "/shared/team_rules/"
```

```toml
[tool.astralint]
extra_rules = ["./custom_rules/", "/shared/team_rules/"]
```

---

### `include`

**Type:** `list[string]`  
**Default:** `["**/*.cdf"]`

Glob patterns for files to include when linting a directory.

```yaml
include:
  - "**/*.cdf"
  - "data/**/*.cdf"
```

---

### `exclude`

**Type:** `list[string]`  
**Default:** `[]`

Glob patterns for files to exclude when linting a directory.

```yaml
exclude:
  - "**/test_data/**"
  - "**/*_backup.cdf"
  - "**/old/**"
```

---

### `output`

Output configuration options.

#### `output.format`

**Type:** `string`  
**Default:** `"console"`

Output format for the validation report.

```yaml
output:
  format: console
```

**Valid formats:** `console`, `html`, `json`

#### `output.verbose`

**Type:** `boolean`  
**Default:** `false`

Show detailed output including which config file is being used.

```yaml
output:
  verbose: true
```

#### `output.show_passed`

**Type:** `boolean`  
**Default:** `true`

Include passing checks in the report.

```yaml
output:
  show_passed: false  # Only show failures
```

#### `output.dest`

**Type:** `path | null`  
**Default:** `null`

Destination file for the report (for `html` and `json` formats).

```yaml
output:
  format: html
  dest: "./reports/validation.html"
```

---

## Complete Examples

### `.astralint.yaml`

```yaml
# AstraLint Configuration

suite: ISTP

# Only run these rules
select:
  - "MandatoryGlobalAttributes"
  - "MandatoryVariableAttributes"
  - "ISTP-VAR-.*"

# Demote some errors to warnings
severity_overrides:
  ISTP-VAR-001: WARNING
  ISTP-VAR-002: WARNING

# Load custom rules
extra_rules:
  - "./custom_rules/"

# File patterns
include:
  - "**/*.cdf"

exclude:
  - "**/test_data/**"
  - "**/examples/**"

# Output settings
output:
  format: console
  verbose: true
  show_passed: false
```

### `pyproject.toml`

```toml
[tool.astralint]
suite = "ISTP"
select = ["MandatoryGlobalAttributes", "ISTP-VAR-.*"]
ignore = []

[tool.astralint.severity_overrides]
"ISTP-VAR-001" = "WARNING"

[tool.astralint.output]
format = "console"
verbose = true
show_passed = false
```

---

## CLI Reference

### `astralint config init`

Generate a starter `.astralint.yaml` configuration file in the project root.

```bash
astralint config init           # Create new config
astralint config init --force   # Overwrite existing config
```

### `astralint config validate`

Validate a configuration file for syntax errors and unknown options.

```bash
astralint config validate                    # Auto-detect config file
astralint config validate --path ./my.yaml   # Validate specific file
```

### `astralint config show`

Display the resolved configuration after merging all sources.

```bash
astralint config show                    # Show merged config
astralint config show --path ./my.yaml   # Show config from specific file
```

---

## Environment-Specific Configs

You can maintain different configs for different environments:

```
project/
├── .astralint.yaml           # Default/development config
├── .astralint.prod.yaml      # Production config (stricter)
└── .astralint.ci.yaml        # CI config (all checks)
```

Use the `--config-file` flag to select:

```bash
# In CI pipeline
astralint lint data/ --config-file .astralint.ci.yaml

# For production validation
astralint lint data/ --config-file .astralint.prod.yaml
```

---

## Tips

1. **Start with defaults** - Run `astralint config init` to generate a documented starter config.

2. **Use `--verbose`** - When debugging, use `--verbose` to see which config file is being loaded.

3. **Validate early** - Run `astralint config validate` after editing your config to catch errors.

4. **Use `select` for focused checks** - When fixing issues incrementally, use `select` to run only specific rules.

5. **Use `severity_overrides` for migration** - When adopting AstraLint on existing projects, demote errors to warnings initially.

---

## Exit Codes

AstraLint returns appropriate exit codes for CI/CD integration:

| Exit Code | Meaning |
|-----------|---------|
| 0 | All checks passed |
| 1 | One or more ERROR-level failures |

### Strict Mode

By default, only ERROR-level failures cause a non-zero exit code. Use `--strict` to also fail on warnings:

```bash
# Normal mode: exit 1 only on errors
astralint lint data.cdf

# Strict mode: exit 1 on errors OR warnings
astralint lint data.cdf --strict
```

This is useful in CI pipelines where you want to enforce all recommendations.
