<h1 align="center">
<img src="https://raw.githubusercontent.com/SciQLop/AstraLint/main/logo.png" width="300">
</h1><br>

# AstraLint

AstraLint is a Python linter for Space Physics data schemas such as ISTP or PDS.

The core idea is to run a set of checks on a data file using a common abstract representation of the data.
The data representation is described in [src/astralint/base/file.py](src/astralint/base/file.py), each codec transforms a specific file format into that representation.

Suites are defined in [src/astralint/suites](src/astralint/suites), they are automatically discovered at runtime, each suite is a collection of rules,
you can find an example of a rule in [src/astralint/suites/ISTP/rules/global_attributes/rules_mandatory_attributes.py](src/astralint/suites/ISTP/rules/global_attributes/rules_mandatory_attributes.py).

* * *

## Project Docs

For how to install uv and Python, see [installation.md](docs/installation.md).

For development workflows, see [development.md](docs/development.md).

For instructions on publishing to PyPI, see [publishing.md](docs/publishing.md).

* * *

*This project was built from
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
