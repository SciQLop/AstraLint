"""Regression tests for ISTP false-positive fixes (case/format strictness).

Each rule below was firing on real, standards-compliant CDAWeb data. The fixes
relax them to what the ISTP doc actually permits; these tests pin the accepted
forms while keeping the genuinely-malformed ones rejected.
"""

from astralint.base import get_suite
from astralint.base.file import Attribute, DataType, File, Variable
from astralint.resolver.engine import _iter_failures


def _fires(file: File, reference: str) -> bool:
    suite = get_suite("ISTP")
    assert suite is not None
    res = suite.run(file)
    return any(ref == reference for ref, _leaf in _iter_failures(res.failures_only()))


def _global(name: str, value: str) -> File:
    return File(
        extension="cdf",
        filename="x.cdf",
        compression="NONE",
        variables={},
        attributes={
            name: Attribute(name=name, data_type=[DataType.CHAR], shape=[1], values=[value])
        },
    )


def _var_attr(attr: str, value: str) -> File:
    return File(
        extension="cdf",
        filename="x.cdf",
        compression="NONE",
        attributes={},
        variables={
            "v": Variable(
                name="v",
                shape=[10],
                compression="NONE",
                data_type=DataType.FLOAT32,
                record_variance=True,
                attributes={
                    attr: Attribute(name=attr, data_type=[DataType.CHAR], shape=[1], values=[value])
                },
            )
        },
    )


# ---- GA-004: Logical_file_id format is case-insensitive (canonical uppercase ids) ----


def test_ga004_accepts_uppercase_canonical_ids():
    for value in (
        "AC_H2_SIS_20101105_V06",  # ACE
        "GE_K0_CPI_19921231_V02",  # Geotail
        "solo_L1_rpw-lfr-surv-asm_20200617_V03",  # Solar Orbiter (mixed case)
    ):
        assert not _fires(_global("Logical_file_id", value), "ISTP-GA-004"), value


def test_ga004_still_rejects_malformed():
    assert _fires(_global("Logical_file_id", "not a valid logical file id"), "ISTP-GA-004")


# ---- GA-017: lowercase is only a (soft) recommendation ----


def test_ga017_warns_on_uppercase_but_not_lowercase():
    assert _fires(_global("Logical_file_id", "AC_H2_SIS_20101105_V06"), "ISTP-GA-017")
    assert not _fires(_global("Logical_file_id", "ac_h2_sis_20101105_v06"), "ISTP-GA-017")


# ---- VA-005: DISPLAY_TYPE may carry ">" plot params; case/space tolerant ----


def test_va005_accepts_parameterized_and_cased_display_type():
    for value in (
        "spectrogram>y=energy,z=Flux_H(*,1)",  # the doc's own example form
        "TIME_SERIES",
        "time_series ",
    ):
        assert not _fires(_var_attr("DISPLAY_TYPE", value), "ISTP-VA-005"), value


def test_va005_still_rejects_unknown_type():
    assert _fires(_var_attr("DISPLAY_TYPE", "bogus_plot"), "ISTP-VA-005")


# ---- VA-010: FORMAT accepts valid Fortran in any case (+ Z hex, nP scale) ----


def test_va010_accepts_valid_fortran_variants():
    for value in ("f12.8", "a5", "1PE9.2", "Z10.8", "F5.2   ", "I10"):
        assert not _fires(_var_attr("FORMAT", value), "ISTP-VA-010"), value


def test_va010_still_rejects_widthless_and_garbage():
    assert _fires(_var_attr("FORMAT", "I"), "ISTP-VA-010")  # no width
    assert _fires(_var_attr("FORMAT", "not-a-format"), "ISTP-VA-010")


# ---- GA-009: Discipline validated by structure, not an incomplete allow-list ----


def test_ga009_accepts_non_space_physics_disciplines():
    for value in (
        "Planetary Physics>Particles",
        "Solar Physics>Interplanetary Studies",
        "Heliospheric Physics>Particles",
        "Space Physics>Planetary Physics>Particles",  # multi-level
    ):
        assert not _fires(_global("Discipline", value), "ISTP-GA-009"), value


def test_ga009_still_rejects_unstructured():
    assert _fires(_global("Discipline", "nonsense"), "ISTP-GA-009")
