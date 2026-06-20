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
