# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is AstraLint?

A Python linter for Space Physics data files (CDF, FITS) that validates conformance to standards like ISTP, PDS4, and SOLARNET. It uses a codec-agnostic architecture: file formats are transformed into an abstract `File` model (Pydantic), then validated against declarative YAML-based rules.

## Commands

```bash
make                    # install + lint + test (full dev workflow)
make install            # uv sync --all-extras
make lint               # devtools/lint.py (codespell → ruff check --fix → ruff format → basedpyright)
make test               # pytest
make build              # uv build

uv run pytest tests/test_assertions.py          # run a single test file
uv run pytest tests/test_assertions.py -k name  # run a single test by name
uv run astralint lint myfile.cdf                # run the CLI
uv run astralint fix myfile.cdf --apply none    # dry-run the auto-fixer
```

## Architecture

**Codec → File model → Rules → Results**

1. **Codecs** (`src/astralint/codecs/`): Protocol-based plugin system. Each codec implements `supported_extensions()` and `load()`. Auto-registered via `__init_subclass__`. Currently: CDF (pycdfpp), FITS (astropy).

2. **File model** (`src/astralint/base/file.py`): Pydantic models — `File` contains `attributes` (global metadata) and `variables` (each with its own `attributes`). Path resolution uses regex-based `/`-separated paths (e.g. `variables/.*/attributes/CATDESC`).

3. **Conformance Suites** (`src/astralint/suites/`): Each suite has a `suite.yaml` + `rules/` directory of YAML rule files. Suites support inheritance via `inherit_from`. Rules are lazily loaded via `register_suite()`.

4. **Assertions** (`src/astralint/base/yaml_rules/assertions/`): Discriminated union on the `check` field. Types: `exists`, `not_exists`, `comparison`, `range`, `is_type`, `matches` (regex), `contains_keys`, `in`, `not_in`, `length`, `not_empty`, `requires`, `array_shape`, `reference_variable`. Combinators: `all_of`, `any_of`, `not`.

5. **Results** (`src/astralint/base/validation_result.py`): Tree structure — `ValidationResult` (leaf) and `ValidationResultGroup` (branch). Severities: ERROR, WARNING, INFO, SKIPPED.

6. **Config** (`src/astralint/config/`): Hierarchical merging — CLI args > `.astralint.yaml` > `pyproject.toml [tool.astralint]` > defaults.

7. **Reports** (`src/astralint/reports/`): Rich console output and Jinja2-based HTML reports.

8. **Resolver** (`src/astralint/resolver/`): Turns validation failures into proposed fixes. A declarative `registry.py` (`ResolverEntry` list) maps `(attribute, scope)` + rule-reference triggers to resolver functions in `sources/` (`type_rules`, `graph_rules`, `pointers`, `filename`, `text`). `engine.resolve(file, failures)` walks failing leaves and emits deduped `Fix`es (auto vs staged); `apply.py` mutates a CDF via pycdfpp; `loop.converge()` runs validate→fix→re-validate to a corrected file. Drives the `astralint fix` command and the post-`lint` hint. Numeric/physical and identity/provenance attributes are never fabricated.

## Code Style

- Line length: 100
- Type checker: basedpyright (standard mode)
- Formatter/linter: ruff
- Python: 3.11+ (CI tests 3.11–3.14)
- Package manager: uv
- Build backend: hatchling with uv-dynamic-versioning (version from git tags)

## Extensibility

- **New codec**: implement `Codec` protocol in `src/astralint/codecs/`
- **New assertion**: extend `BaseAssertion` in `src/astralint/base/yaml_rules/assertions/`
- **New suite**: add directory in `src/astralint/suites/` with `suite.yaml` + `rules/`
- **New report format**: add reporter in `src/astralint/reports/`
- **New auto-fix**: add a resolver function in `src/astralint/resolver/sources/` and a `ResolverEntry` in `resolver/registry.py` (triggered by the rule's reference)
