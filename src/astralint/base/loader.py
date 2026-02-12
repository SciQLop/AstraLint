import os
import importlib
import inspect
from glob import glob

def _caller_package():
    frame = inspect.stack()[2]
    module = inspect.getmodule(frame[0])
    return module.__package__

def _make_relative_import_path(module_path: str, package_path:str) -> str:
    relative_path = os.path.relpath(module_path, package_path)
    relative_path = relative_path.replace('../', '..')
    relative_path = relative_path.replace('/', '.')
    return relative_path

def load_rules_from_dir(path: str):
    modules = glob(os.path.join(path, "**/rules_*.py"))
    for module in modules:
        relative_import_path = _make_relative_import_path(module[:-3], os.path.dirname(__file__))
        importlib.import_module(relative_import_path, package=__package__)


def load_suite_from_dir(path: str, suite_name: str):
    try:
        relative_import_path = _make_relative_import_path(os.path.join(path,suite_name), os.path.dirname(__file__))
        importlib.import_module(relative_import_path, package=__package__)
    except ModuleNotFoundError:
        print(f"Suite {suite_name} not found in {path}")

