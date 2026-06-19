<h1 align="center">
<img src="https://raw.githubusercontent.com/SciQLop/AstraLint/main/logo.png" width="300">
</h1><br>

# AstraLint

AstraLint is a Python linter for Space Physics data files, validating conformance to standards such
as [ISTP](https://istp-metadata.readthedocs.io/) and [PDS4](https://pds.nasa.gov/datastandards/documents/).

<p align="center">
  <a href="https://sciqlop.github.io/AstraLint/"><strong>🚀 Try it online — no installation required!</strong></a>
</p>

## Install

AstraLint is published on PyPI. The simplest way to install is with pip:

```bash
pip install astralint
```

Note: PyPI package names are case-insensitive; `pip install AstraLint` also works. If you prefer using a virtual environment, create and activate one before installing.

## Overview

AstraLint validates data files against conformance suites using a **codec-agnostic architecture**:

1. **Codecs** transform file formats (e.g., CDF) into a common abstract representation ([
   `File`](src/astralint/base/file.py))
2. **Suites** define collections of validation rules (e.g., ISTP, PDS4)
3. **Rules** check specific requirements, defined either in Python or YAML

## Usage

```bash
# Lint a file against the default ISTP suite
astralint lint myfile.cdf

# Lint a multiple files at once
astralint lint file1.cdf file2.cdf file3.cdf

# Lint against a specific suite
astralint lint myfile.cdf --suite PDS4

# Select specific rules to run filtering by reference ID or name, regex supported
astralint lint myfile.cdf --suite ISTP --select "ISTP-MD-003" --select ".*GlobalAttributes"

# Ignore specific rules by reference ID or name, regex supported
astralint lint myfile.cdf --suite ISTP --ignore "ISTP-MD-00[0-9]" --ignore "MandatoryGlobalAttributes"

# Show every check, including the ones that passed (full tree)
astralint lint myfile.cdf --show-passed

# Show only failed assertions, pruning passed and skipped from the full tree
astralint lint myfile.cdf --show-passed --failed-only

# List available suites
astralint list-suites

# Strict mode: exit with error on warnings too
astralint lint myfile.cdf --strict
```

By default the console output is **quiet**, like a typical linter: it lists only
the errors and warnings that need attention, sorted by severity, and ends with a
one-line verdict (e.g. `✗ Found 7 problems (3 errors, 4 warnings), plus 13 info
findings`). Use `--show-passed` to see the full nested tree of every check, and
`--output html` for an interactive, filterable report.

AstraLint returns exit code `1` on validation errors (or warnings with `--strict`), making it suitable for CI/CD pipelines.

## Configuration

AstraLint can be configured via `pyproject.toml` or `.astralint.yaml`. Configuration is loaded with the following precedence (highest to lowest):

1. CLI arguments
2. `.astralint.yaml` (project root)
3. `pyproject.toml` `[tool.astralint]`
4. Built-in defaults

### Quick Start

```bash
# Generate a starter config file
astralint config init

# Validate your config file
astralint config validate

# Show resolved configuration (merged from all sources)
astralint config show
```

### Example `.astralint.yaml`

```yaml
suite: ISTP

select:
  - "MandatoryGlobalAttributes"
  - "ISTP-VAR-.*"

ignore:
  - "DeprecatedRule"

severity_overrides:
  ISTP-VAR-001: WARNING

extra_rules:
  - "./custom_rules/"

output:
  format: console
  verbose: false
  show_passed: true
```

### Example `pyproject.toml`

```toml
[tool.astralint]
suite = "ISTP"
select = ["MandatoryGlobalAttributes"]

[tool.astralint.output]
format = "html"
verbose = true
```

📖 **[Full Configuration Reference →](docs/config.md)**

## Architecture

```mermaid
flowchart TD
    subgraph Input["📥 Input"]
        A[📄 Data File]
    end
    
    subgraph Codecs["🔌 Codecs (pluggable)"]
        B1[CDF Codec]
        B2[NetCDF Codec]
        B3[... more]
    end
    
    subgraph Core["⚙️ Core"]
        C[📦 Abstract File Model]
        D[📋 Conformance Suite]
        E[✅ Rules & Assertions]
    end
    
    subgraph Suites["📚 Suites (pluggable)"]
        S1[ISTP]
        S2[PDS4]
        S3[... more]
    end
    
    subgraph Reports["📊 Reports (pluggable)"]
        R1[Console]
        R2[JSON]
        R3[... more]
    end
    
    A --> B1 & B2 & B3
    B1 & B2 & B3 --> C
    C --> D
    S1 & S2 & S3 -.->|loads| D
    D --> E
    E --> R1 & R2 & R3
    
    style C fill:#fff3e0
    style Core fill:#f5f5f5,stroke:#999
    style Codecs fill:#e3f2fd,stroke:#1976d2
    style Suites fill:#fce4ec,stroke:#c2185b
    style Reports fill:#e8f5e9,stroke:#388e3c
```

## File Model

The abstract `File` model is the core data structure that all codecs produce. Rules and assertions operate on this unified representation:

```
File
├── filename: str                            # File name or identifier
├── extension: str                           # File extension (e.g., "cdf")
├── compression: str                     # e.g., "gzip", "none"
├── attributes: {name → Attribute}       # Global metadata
│   ├── "Project"      → Attribute
│   ├── "PI_name"      → Attribute
│   └── ...
└── variables: {name → Variable}         # Data variables
    ├── "Epoch" → Variable
    │   ├── name: str                    # "Epoch"
    │   ├── shape: [int]                 # e.g., [1440]
    │   ├── compression: str             # "gzip", "none"
    │   ├── data_type: DataType          # TT2000, FLOAT64, ...
    │   ├── record_variance: bool
    │   └── attributes: {name → Attribute}
    │       ├── "CATDESC"  → Attribute
    │       ├── "FILLVAL"  → Attribute
    │       └── ...
    ├── "Temperature" → Variable
    └── ...

Attribute
├── name: str
├── data_type: [DataType]                # List of data types
└── shape: [int]                         # Attribute dimensions

DataType = CHAR | UINT8 | UINT16 | UINT32 | UINT64
         | INT8 | INT16 | INT32 | INT64
         | FLOAT32 | FLOAT64
         | TT2000 | CDFEPOCH | CDFEPOCH16
```

### Path Navigation

Rules use `/`-separated paths with regex support to navigate the model:

| Path Example | Description |
|--------------|-------------|
| `attributes` | Global attributes dictionary |
| `attributes/Project` | Specific global attribute |
| `variables` | All variables dictionary |
| `variables/Epoch` | Specific variable |
| `variables/.*/attributes` | Attributes of all variables |
| `variables/Epoch/data_type` | Data type of a specific variable |
| `variables/Epoch/shape/0` | First dimension of variable shape |
| `attributes/Project/data_type/0` | First data type of attribute |

Lists are accessed using numeric indices: `path/to/list/0`, `path/to/list/1`, etc.

## Defining Rules in YAML

Rules can be defined declaratively in YAML files. Example from [
`MandatoryGlobalAttributes.yaml`](src/astralint/suites/ISTP/rules/GlobalAttributes/MandatoryGlobalAttributes.yaml):

```yaml
name: MandatoryGlobalAttributes
description: "All mandatory global attributes must be present"
url: "https://..."
reference: "ISTP-MD-003"
severity: ERROR
suite: ISTP

assertions:
  - path: "attributes"
    check: contains_keys
    keys:
      - Data_type
      - Logical_source
      - PI_name
    message: "Missing mandatory global attribute: {key}"

  - path: "variables/.*/attributes"
    check: contains_keys
    keys: [ CATDESC, FIELDNAM, FILLVAL ]
    message: "Variable missing required attribute: {key}"
```

### Available Assertions

| Category | Checks |
|----------|--------|
| **Existence** | `exists`, `not_exists` |
| **Value** | `comparison`, `range`, `is_type` |
| **String** | `matches` |
| **Collection** | `contains_keys`, `in`, `not_in`, `length`, `not_empty`, `requires`, `array_shape` |
| **Relationship** | `reference_variable`, `compare_to` |
| **Combinators** | `all_of`, `any_of`, `any_match`, `none_of`, `not`, `one_of`, `at_least`, `at_most`, `exactly` |
| **Conditional** | `if_then`, `if_then_else` |

📖 **[Full Assertions Reference →](docs/assertions.md)**

## Supported File Formats

| Format | Extension                | Library                                       |
|--------|--------------------------|-----------------------------------------------|
| CDF    | `.cdf`                   | [pycdfpp](https://github.com/SciQLop/pycdfpp) |
| FITS   | `.fits`, `.fit`, `.fts`  | [astropy](https://www.astropy.org/)           |

## Available Conformance Suites (WIP/Demo)

- **ISTP** - [ISTP Metadata Guidelines](https://istp-metadata.readthedocs.io/)
- **CDAWeb** - [CDAWeb](https://cdaweb.gsfc.nasa.gov/) ingestion profile: inherits ISTP and promotes the CDAWeb-required attributes (`Instrument_type`, `Mission_group`) to errors, plus CDAWeb-specific entry limits
- **PDS4** - [Planetary Data System v4](https://pds.nasa.gov/datastandards/documents/)
- **SOLARNET** - [SOLARNET Metadata Recommendations](https://solarnet.readthedocs.io/en/stable/index.html)

## Extending AstraLint

### Adding a New Codec

Create a new codec in `src/astralint/codecs/`. Subclasses register themselves
automatically via `__init_subclass__`, so simply defining the class and importing
the module is enough to make the codec available:

```python
from astralint.base import Codec, File


class MyCodec(Codec):
    @classmethod
    def supported_extensions(cls) -> list[str]:
        return ["ext"]

    @staticmethod
    def load(file_url_or_bytes: str | bytes) -> File | None:
        # Transform your file format into the abstract File model
        ...
```

For remote files, AstraLint provides `get_remote_file(url) -> bytes` to fetch
remote content and `is_remote_file(url) -> bool` to detect URLs.

### Adding a New Assertion Type

Create a new assertion in `src/astralint/base/yaml_rules/assertions/`. Subclasses
of `BaseAssertion` are auto-registered into the discriminated union via the
`check` field's Literal value:

```python
from typing import Any, Literal

from astralint.base import File, Severity, ValidationResult
from astralint.base.yaml_rules.assertions.base import BaseAssertion


class MyAssertion(BaseAssertion):
    check: Literal["my_check"] = "my_check"

    # Add custom fields as needed; they are populated from the YAML rule definition.
    # expected_value: Any

    def single_assertion(
        self,
        file: File,
        path: str,
        value: Any,
        severity: Severity,
        captures: dict[str, str] | None = None,
    ) -> ValidationResult:
        # Called once per (path, value) pair that matched the base assertion's path
        # pattern. `captures` holds named groups from {name} placeholders, if any.
        ...
```

* * *

## Project Docs

For how to install uv and Python, see [installation.md](docs/installation.md).

For development workflows, see [development.md](docs/development.md).

For instructions on publishing to PyPI, see [publishing.md](docs/publishing.md).

* * *

*This project was built from
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
