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
