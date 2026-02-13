import os
import importlib
import inspect
from glob import glob
from pathlib import Path

from ..logger import get_logger

log = get_logger(__name__)


def _caller_package():
    frame = inspect.stack()[2]
    module = inspect.getmodule(frame[0])
    return module.__package__


def _make_relative_import_path(module_path: str, package_path: str) -> str:
    relative_path = os.path.relpath(module_path, package_path)
    relative_path = relative_path.replace('../', '..')
    relative_path = relative_path.replace('/', '.')
    return relative_path


def load_rules_from_dir(path: str):
    modules = glob(os.path.join(path, "**/rules_*.py"))
    for module in modules:
        log.debug(f"Loading rule from {module}")
        relative_import_path = _make_relative_import_path(module[:-3], os.path.dirname(__file__))
        importlib.import_module(relative_import_path, package=__package__)

    yaml_rules = glob(os.path.join(path, "**/*.yaml")) + glob(os.path.join(path, "**/*.yml"))
    log.debug(f"Found {len(yaml_rules)} YAML rule files in {path}")
    for yaml_rule in yaml_rules:
        from .yaml_rules import register_yaml_rule
        log.debug(f"Loading YAML rule from {yaml_rule}")
        register_yaml_rule(Path(yaml_rule))


def load_suite_from_dir(path: str, suite_name: str):
    log.debug(f"Looking for suite {suite_name} in {path}")
    suite_dir = os.path.join(path, suite_name)
    yaml_suite = glob(os.path.join(suite_dir, "*.yaml")) + glob(os.path.join(suite_dir, "*.yml"))
    if len(yaml_suite) == 0 and os.path.exists(os.path.join(path, "__init__.py")):
        try:
            relative_import_path = _make_relative_import_path(os.path.join(suite_dir), os.path.dirname(__file__))
            importlib.import_module(relative_import_path, package=__package__)
        except ModuleNotFoundError:
            log.error(f"Suite {suite_name} not found in {path}")
    elif len(yaml_suite) == 1:
        from .conformance_suite import load_suite_from_yaml
        from . import register_suite
        log.debug(f"Loading suite from {yaml_suite[0]}")
        suite = load_suite_from_yaml(yaml_suite[0])
        register_suite(description=suite.description, url=suite.url, rules_lookup_dir=os.path.join(suite_dir, "rules"),
                       name=suite.name, inherit_from=suite.inherit_from)
