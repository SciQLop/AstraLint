try:
    from glob import glob

    import pytest
    from pytest_pyodide import run_in_pyodide  # type: ignore
    from pytest_pyodide.decorator import copy_files_to_pyodide  # type: ignore

    _FILE_PATH = glob("pyodide-dist/astralint*.whl", recursive=True)[0]
    _DEST_PATH = _FILE_PATH.split("/")[-1]

    @pytest.mark.driver_timeout(60 * 2)
    @copy_files_to_pyodide(
        file_list=[(_FILE_PATH, _DEST_PATH)], install_wheels=True, recurse_directories=True
    )
    @run_in_pyodide(packages=["micropip", "pycdfpp"])
    async def test_import_astralint(selenium):
        from astralint.base import list_all_suites

        assert len(list_all_suites()) > 0


except ImportError:
    print("pytest-pyodide is not installed; skipping Pyodide tests.")
