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

    @pytest.mark.driver_timeout(60 * 3)
    @run_in_pyodide(packages=["micropip"])
    async def test_pycdfpp_mutation_under_pyodide(selenium):
        # The auto-fixer's apply path (apply_fixes/converge) is a pure-Python
        # wrapper over pycdfpp's CDF / add_attribute / set_value / save. Validate
        # those work under emscripten — the prerequisite for an in-browser
        # apply+download. (Tests pycdfpp directly; the resolver itself is pure
        # Python and exercised by the non-wasm suite.)
        import micropip  # type: ignore

        await micropip.install("pycdfpp")

        import numpy as np
        import pycdfpp

        cdf = pycdfpp.CDF()
        cdf.add_variable("flux", np.arange(10, dtype=np.float32), pycdfpp.DataType.CDF_FLOAT)
        cdf["flux"].add_attribute("SCALETYP", "linear")  # CHAR add
        cdf["flux"].add_attribute(
            "FILLVAL", np.array([-1e31], dtype=np.float32), pycdfpp.DataType.CDF_FLOAT
        )  # numeric add
        cdf.add_attribute("Project", ["Test>Test"], [pycdfpp.DataType.CDF_CHAR])  # global add
        out = bytes(pycdfpp.save(cdf))

        reloaded = pycdfpp.load(out)
        assert "SCALETYP" in reloaded["flux"].attributes
        assert "FILLVAL" in reloaded["flux"].attributes
        assert "Project" in reloaded.attributes


except ImportError:
    print("pytest-pyodide is not installed; skipping Pyodide tests.")
