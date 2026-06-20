import os
from pathlib import Path

from astralint.astralint import fix as fix_command

__HERE__ = os.path.dirname(__file__)
_CDF = os.path.join(__HERE__, "resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf")


def test_fix_dry_run_writes_nothing(tmp_path, capsys):
    out = tmp_path / "fixed.cdf"
    fix_command(Path(_CDF), suite="ISTP", apply="none", output=out)
    assert not out.exists()


def test_fix_auto_writes_corrected_cdf(tmp_path):
    out = tmp_path / "fixed.cdf"
    fix_command(Path(_CDF), suite="ISTP", apply="auto", output=out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_fix_rejects_invalid_apply(tmp_path):
    import pytest

    with pytest.raises(SystemExit):
        fix_command(Path(_CDF), suite="ISTP", apply="bogus", output=tmp_path / "x.cdf")


def test_fix_line_escapes_file_derived_markup():
    # CDF metadata can contain '['/']'; Rich would treat it as markup. The fix
    # line must escape target_path / value / provenance_note (issue from review).
    from astralint.astralint import _fix_line
    from astralint.resolver.models import Fix, ReferenceSource, Scope

    # Use tag-like brackets ([red], [bad], [zap]) — those are what Rich would
    # interpret as markup; escape() must backslash them.
    fx = Fix(
        target_path="variables/x[red]y/attributes/Y",
        variable="x[red]y",
        attribute="Y",
        scope=Scope.VARIABLE,
        action="add",
        value="[bad]",
        source=ReferenceSource.TYPE_RULE,
        confidence=1.0,
        provenance_note="see [zap]",
        auto=True,
    )
    line = _fix_line(fx, staged=False)
    assert "x\\[red]y" in line  # target_path tag-like bracket escaped
    assert "\\[bad]" in line  # value bracket escaped
    assert "see \\[zap]" in line  # provenance bracket escaped


def test_fix_hint_reports_auto_fixes():
    from astralint.astralint import _fix_hint
    from astralint.base import get_suite, load_file

    p = Path(_CDF)
    file = load_file(str(p))
    suite = get_suite("ISTP")
    assert file is not None and suite is not None
    hint = _fix_hint([(p, file, suite.run(file))])
    assert hint is not None
    assert "auto-fixable" in hint
    assert "astralint fix" in hint


def test_fix_hint_none_when_nothing_to_fix():
    from astralint.astralint import _fix_hint

    assert _fix_hint([]) is None


def test_fix_hint_skips_non_cdf_files():
    from astralint.astralint import _fix_hint
    from astralint.base import get_suite, load_file

    p = Path(_CDF)
    file = load_file(str(p))
    suite = get_suite("ISTP")
    assert file is not None and suite is not None
    non_cdf = file.model_copy(update={"extension": "fits"})
    assert _fix_hint([(p, non_cdf, suite.run(file))]) is None


def test_lint_prints_fix_hint(capsys):
    import pytest

    from astralint.astralint import lint

    with pytest.raises(SystemExit):  # the resource file has errors -> exit 1
        lint([Path(_CDF)], suite="ISTP")
    assert "astralint fix" in capsys.readouterr().out


def test_fix_hint_counts_user_disposition():
    from astralint.astralint import _fix_hint
    from astralint.base import get_suite, load_file

    p = Path(_CDF)
    file = load_file(str(p))
    suite = get_suite("ISTP")
    assert file is not None and suite is not None
    # construct a file missing a recommended provenance global so a USER fix fires
    file.attributes.pop("DOI", None)
    hint = _fix_hint([(p, file, suite.run(file))])
    assert hint is not None
