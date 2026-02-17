## Installing uv and Python

This project is set up to use [**uv**](https://docs.astral.sh/uv/), the new package
manager for Python. `uv` replaces traditional use of `pyenv`, `pipx`, `poetry`, `pip`,
etc. This is a quick cheat sheet on that:

On macOS or Linux, if you don't have `uv` installed, a quick way to install it:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

For macOS, you prefer [brew](https://brew.sh/) you can install or upgrade uv with:

```shell
brew update
brew install uv
```

See [uv's docs](https://docs.astral.sh/uv/getting-started/installation/) for more
installation methods and platforms.

Now you can use uv to install a current Python environment:

```shell
uv python install 3.13 # Or pick another version.
```

## Installing AstraLint from PyPI

AstraLint is published on PyPI. The simplest way to install it is with pip (recommended inside a virtual environment):

```bash
python -m venv .venv
source .venv/bin/activate
pip install astralint
```

PyPI package names are case-insensitive so `pip install AstraLint` also works. If you prefer to develop from source, install the project in editable mode:

```bash
pip install -e .[dev]
```
