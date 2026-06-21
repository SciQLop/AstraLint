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
    # pycdfpp ships emscripten wheels on PyPI but is not part of the Pyodide
    # distribution, so it cannot be loadPackage'd; it is resolved from PyPI by
    # micropip when the astralint wheel is installed (install_wheels=True).
    @run_in_pyodide(packages=["micropip"])
    async def test_import_astralint(selenium):
        from astralint.base import list_all_suites

        assert len(list_all_suites()) > 0

    @pytest.mark.driver_timeout(60 * 2)
    @copy_files_to_pyodide(
        file_list=[(_FILE_PATH, _DEST_PATH)], install_wheels=True, recurse_directories=True
    )
    @run_in_pyodide(packages=["micropip"])
    async def test_resolver_mutation_under_pyodide(selenium):
        # Validates that the resolver's mutation surface works in the browser:
        # pycdfpp.save / add_attribute / set_value (used by apply_fixes/converge)
        # must be available in the emscripten build for an in-browser auto-fixer.
        import numpy as np
        import pycdfpp

        from astralint.base import get_suite
        from astralint.codecs.cdf import CdfCodec
        from astralint.resolver.engine import resolve
        from astralint.resolver.loop import converge

        cdf = pycdfpp.CDF()
        cdf.add_variable("flux", np.arange(10, dtype=np.float32), pycdfpp.DataType.CDF_FLOAT)
        cdf["flux"].add_attribute("VAR_TYPE", "data")
        cdf.add_attribute("Project", ["Test>Test"], [pycdfpp.DataType.CDF_CHAR])
        data = bytes(pycdfpp.save(cdf))

        suite = get_suite("ISTP")
        assert suite is not None
        file = CdfCodec.load(data)
        assert file is not None
        # read-only proposal path (metadata only)
        assert isinstance(resolve(file, suite.run(file).failures_only()), list)
        # mutation path: add/set attributes + save back to bytes
        report, out = converge(data, suite, max_iter=3, filename="x.cdf")
        assert isinstance(out, bytes)


except ImportError:
    print("pytest-pyodide is not installed; skipping Pyodide tests.")
