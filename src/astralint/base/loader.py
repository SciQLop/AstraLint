import importlib
import inspect
import os.path
from pathlib import Path

from ..logger import get_logger

log = get_logger(__name__)

_BASE_DIR = Path(__file__).parent


def _caller_package():
    frame = inspect.stack()[2]
    module = inspect.getmodule(frame[0])
    if module is None:
        raise RuntimeError("Could not determine caller package")
    return module.__package__


def _make_relative_import_path(module_path: Path, package_path: Path) -> str:
    # os.path.relpath handles paths that traverse sibling trees ('..'), which
    # Path.relative_to does not in Python <3.12. Once 3.12 is the minimum
    # supported version, switch to Path.relative_to(..., walk_up=True).
    relative = os.path.relpath(module_path, package_path)
    return relative.replace("../", "..").replace("/", ".")


def load_rules_from_dir(path: str | Path):
    root = Path(path)
    for module in root.rglob("rules_*.py"):
        log.debug(f"Loading rule from {module}")
        importlib.import_module(
            _make_relative_import_path(module.with_suffix(""), _BASE_DIR),
            package=__package__,
        )

    yaml_rules = list(root.rglob("*.yaml")) + list(root.rglob("*.yml"))
    log.debug(f"Found {len(yaml_rules)} YAML rule files in {root}")
    for yaml_rule in yaml_rules:
        from .yaml_rules import register_yaml_rule

        log.debug(f"Loading YAML rule from {yaml_rule}")
        register_yaml_rule(yaml_rule)


def load_suite_from_dir(path: str | Path, suite_name: str):
    root = Path(path)
    log.debug(f"Looking for suite {suite_name} in {root}")
    suite_dir = root / suite_name
    yaml_suite = list(suite_dir.glob("*.yaml")) + list(suite_dir.glob("*.yml"))
    if not yaml_suite and (root / "__init__.py").exists():
        try:
            importlib.import_module(
                _make_relative_import_path(suite_dir, _BASE_DIR), package=__package__
            )
        except ModuleNotFoundError:
            log.error(f"Suite {suite_name} not found in {root}")
    elif len(yaml_suite) == 1:
        from . import register_suite
        from .conformance_suite import load_suite_from_yaml

        log.debug(f"Loading suite from {yaml_suite[0]}")
        suite = load_suite_from_yaml(str(yaml_suite[0]))
        register_suite(
            description=suite.description,
            url=suite.url,
            rules_lookup_dir=str(suite_dir / "rules"),
            name=suite.name,
            inherit_from=suite.inherit_from,
        )
