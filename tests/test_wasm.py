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

    @pytest.mark.driver_timeout(60 * 4)
    @run_in_pyodide(packages=["micropip"])
    async def test_resolver_mutation_under_pyodide(selenium):
        # Validates the in-browser auto-fixer the same way the online demo runs:
        # install astralint + pycdfpp from PyPI, exercise resolve (read-only) and
        # converge (mutation -> pycdfpp save/add_attribute under emscripten). The
        # assertion message carries a diagnostic (which astralint is active) if
        # the resolver subpackage is somehow absent.
        import os

        import micropip  # type: ignore

        await micropip.install(["astralint", "pycdfpp"])

        import astralint

        pkg_dir = os.path.dirname(astralint.__file__)
        version = getattr(astralint, "__version__", "?")
        assert "resolver" in os.listdir(pkg_dir), (
            f"astralint {version} at {pkg_dir} has no resolver: {sorted(os.listdir(pkg_dir))}"
        )

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
        assert isinstance(resolve(file, suite.run(file).failures_only()), list)  # read-only path
        report, out = converge(data, suite, max_iter=3, filename="x.cdf")  # mutation path
        assert isinstance(out, bytes)


except ImportError:
    print("pytest-pyodide is not installed; skipping Pyodide tests.")
