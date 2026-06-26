"""Reproducer tests for the ISTP rule-correctness review.

Each test pins a specific finding from the audit of the ISTP suite against the
IHDE-Alliance ISTP_metadata guidelines (docs/source/03-05). They are written to
fail against the pre-review rules and pass once the corresponding fix lands.
"""

from pathlib import Path

import astralint
from astralint.base.file import Attribute, DataType, File, Variable
from astralint.base.yaml_rules.yaml_rule import load_yaml_rule

RULES_DIR = Path(astralint.__file__).parent / "suites" / "ISTP" / "rules"


def load_rule(category: str, name: str):
    return load_yaml_rule(RULES_DIR / category / f"{name}.yaml")


def attr(name: str, values: list, dtype: DataType = DataType.CHAR) -> Attribute:
    return Attribute(name=name, data_type=[dtype], shape=[len(values)], values=values)


def var(
    name: str,
    var_type: str | None = None,
    attrs: dict | None = None,
    data_type: DataType = DataType.FLOAT64,
    record_variance: bool = True,
    shape: list[int] | None = None,
) -> Variable:
    attributes = dict(attrs or {})
    if var_type is not None:
        attributes["VAR_TYPE"] = attr("VAR_TYPE", [var_type])
    return Variable(
        name=name,
        attributes=attributes,
        compression="NONE",
        data_type=data_type,
        record_variance=record_variance,
        shape=shape or [1],
    )


def make_file(global_attrs: dict | None = None, variables: dict | None = None) -> File:
    return File(
        extension="cdf",
        filename="test.cdf",
        compression="NONE",
        attributes=dict(global_attrs or {}),
        variables=dict(variables or {}),
    )


_FULL_DATA_ATTRS = {
    "CATDESC": attr("CATDESC", ["A fine data variable"]),
    "FIELDNAM": attr("FIELDNAM", ["Data"]),
    "DEPEND_0": attr("DEPEND_0", ["Epoch"]),
    "DISPLAY_TYPE": attr("DISPLAY_TYPE", ["time_series"]),
    "FORMAT": attr("FORMAT", ["F10.2"]),
    "LABLAXIS": attr("LABLAXIS", ["B"]),
    "UNITS": attr("UNITS", ["nT"]),
    "VALIDMIN": attr("VALIDMIN", [0.0], DataType.FLOAT64),
    "VALIDMAX": attr("VALIDMAX", [100.0], DataType.FLOAT64),
    "FILLVAL": attr("FILLVAL", [-1e31], DataType.FLOAT64),
}


# --- Engine: per-variable conditional correlation (DataVariableAttributes) ----


def test_data_variable_rule_runs_on_mixed_type_file():
    """A data variable missing DEPEND_0 must be flagged even when other variables
    have a different VAR_TYPE (the if_then must correlate per-variable)."""
    broken = dict(_FULL_DATA_ATTRS)
    del broken["DEPEND_0"]
    f = make_file(
        variables={
            "Flux": var("Flux", "data", broken),
            "Flux_labels": var("Flux_labels", "metadata", data_type=DataType.CHAR),
        }
    )
    rule = load_rule("VariableAttributes", "DataVariableAttributes")
    assert not rule.check(f).valid


def test_data_variable_rule_passes_compliant_data_in_mixed_file():
    f = make_file(
        variables={
            "Flux": var("Flux", "data", _FULL_DATA_ATTRS),
            "Flux_labels": var("Flux_labels", "metadata", data_type=DataType.CHAR),
        }
    )
    rule = load_rule("VariableAttributes", "DataVariableAttributes")
    assert rule.check(f).valid


# --- SupportData: RV-only VALIDMIN/MAX and time-type UNITS/FORMAT exemption ---


def test_support_data_validmin_only_required_when_record_varying():
    """Time-invariant support_data does not require VALIDMIN/VALIDMAX."""
    f = make_file(
        variables={
            "Energy": var(
                "Energy",
                "support_data",
                {
                    "CATDESC": attr("CATDESC", ["Energy table"]),
                    "FIELDNAM": attr("FIELDNAM", ["Energy"]),
                    "FORMAT": attr("FORMAT", ["F10.2"]),
                    "UNITS": attr("UNITS", ["keV"]),
                    "LABLAXIS": attr("LABLAXIS", ["E"]),
                },
                record_variance=False,
            )
        }
    )
    rule = load_rule("VariableAttributes", "SupportDataVariableAttributes")
    assert rule.check(f).valid


def test_support_data_rv_missing_validmin_fails():
    f = make_file(
        variables={
            "Energy": var(
                "Energy",
                "support_data",
                {
                    "CATDESC": attr("CATDESC", ["Energy table"]),
                    "FIELDNAM": attr("FIELDNAM", ["Energy"]),
                    "FORMAT": attr("FORMAT", ["F10.2"]),
                    "UNITS": attr("UNITS", ["keV"]),
                    "LABLAXIS": attr("LABLAXIS", ["E"]),
                },
                record_variance=True,
            )
        }
    )
    rule = load_rule("VariableAttributes", "SupportDataVariableAttributes")
    assert not rule.check(f).valid


def test_support_data_time_type_exempt_from_units_and_format():
    """An epoch support_data variable (CDF time type) needs neither UNITS nor FORMAT."""
    f = make_file(
        variables={
            "Epoch": var(
                "Epoch",
                "support_data",
                {
                    "CATDESC": attr("CATDESC", ["Time"]),
                    "FIELDNAM": attr("FIELDNAM", ["Epoch"]),
                    "LABLAXIS": attr("LABLAXIS", ["Epoch"]),
                    "VALIDMIN": attr("VALIDMIN", [0], DataType.TT2000),
                    "VALIDMAX": attr("VALIDMAX", [1], DataType.TT2000),
                },
                data_type=DataType.TT2000,
                record_variance=True,
            )
        }
    )
    rule = load_rule("VariableAttributes", "SupportDataVariableAttributes")
    assert rule.check(f).valid


# --- Metadata rule actually runs ---------------------------------------------


def test_metadata_variable_missing_format_fails():
    f = make_file(
        variables={
            "Labels": var(
                "Labels",
                "metadata",
                {
                    "CATDESC": attr("CATDESC", ["Component labels"]),
                    "FIELDNAM": attr("FIELDNAM", ["Labels"]),
                },
                data_type=DataType.CHAR,
                record_variance=False,
            ),
            "Flux": var("Flux", "data", _FULL_DATA_ATTRS),
        }
    )
    rule = load_rule("VariableAttributes", "MetadataVariableAttributes")
    assert not rule.check(f).valid


# --- MandatoryVariableAttributes: RV FILLVAL + time-type FORMAT exemption -----


def test_rv_variable_missing_fillval_flagged_in_mixed_file():
    rv_attrs = {
        "CATDESC": attr("CATDESC", ["Counts"]),
        "FIELDNAM": attr("FIELDNAM", ["Counts"]),
        "VAR_TYPE": attr("VAR_TYPE", ["data"]),
        "FORMAT": attr("FORMAT", ["I10"]),
    }
    static_attrs = {
        "CATDESC": attr("CATDESC", ["Static"]),
        "FIELDNAM": attr("FIELDNAM", ["Static"]),
        "VAR_TYPE": attr("VAR_TYPE", ["support_data"]),
        "FORMAT": attr("FORMAT", ["I10"]),
    }
    f = make_file(
        variables={
            "Counts": var("Counts", attrs=rv_attrs, record_variance=True),
            "Static": var("Static", attrs=static_attrs, record_variance=False),
        }
    )
    rule = load_rule("VariableAttributes", "MandatoryVariableAttributes")
    assert not rule.check(f).valid


def test_time_type_variable_exempt_from_format():
    """CDF time-type variables do not require FORMAT/FORM_PTR."""
    f = make_file(
        variables={
            "Epoch": var(
                "Epoch",
                "support_data",
                {
                    "CATDESC": attr("CATDESC", ["Time"]),
                    "FIELDNAM": attr("FIELDNAM", ["Epoch"]),
                },
                data_type=DataType.TT2000,
                record_variance=True,
            )
        }
    )
    rule = load_rule("VariableAttributes", "MandatoryVariableAttributes")
    # No FORMAT/FORM_PTR, but Epoch is a time type -> the FORMAT requirement must not fire.
    # (FILLVAL is still required for RV; provide it so we isolate the FORMAT exemption.)
    f.variables["Epoch"].attributes["FILLVAL"] = attr(
        "FILLVAL", [-9223372036854775808], DataType.TT2000
    )
    assert rule.check(f).valid


# --- Global attribute format regexes -----------------------------------------


def test_data_type_accepts_hyphen_and_lowercase():
    for value in ["L2-Summary>level 2 summary", "l2-gms-62ms>gms data"]:
        f = make_file({"Data_type": attr("Data_type", [value])})
        rule = load_rule("GlobalAttributes", "DataTypeFormat")
        assert rule.check(f).valid, value


def test_logical_file_id_accepts_hyphen_in_descriptor():
    f = make_file(
        {"Logical_file_id": attr("Logical_file_id", ["psp_isois_l2-summary_20180928_v07"])}
    )
    rule = load_rule("GlobalAttributes", "LogicalFileIdFormat")
    assert rule.check(f).valid


def test_project_accepts_space_and_lowercase_short_name():
    for value in ["STSP Cluster>Solar Terrestrial Science Programmes, Cluster", "CDAWxx>Workshop"]:
        f = make_file({"Project": attr("Project", [value])})
        rule = load_rule("GlobalAttributes", "ProjectFormat")
        assert rule.check(f).valid, value


def test_project_format_is_warning():
    rule = load_rule("GlobalAttributes", "ProjectFormat")
    assert rule.severity.value == "WARNING"


# --- Controlled lists ---------------------------------------------------------


def test_instrument_type_accepts_dust_and_debris():
    f = make_file({"Instrument_type": attr("Instrument_type", ["Dust and Debris"])})
    rule = load_rule("GlobalAttributes", "InstrumentTypeValues")
    assert rule.check(f).valid


# --- Messages / semantics -----------------------------------------------------


def test_units_single_space_passes_and_message_drops_unitless():
    f = make_file(variables={"B": var("B", "data", {"UNITS": attr("UNITS", [" "])})})
    rule = load_rule("VariableAttributes", "UnitsNotEmpty")
    assert rule.check(f).valid
    src = (RULES_DIR / "VariableAttributes" / "UnitsNotEmpty.yaml").read_text()
    assert "unitless" not in src


def test_text_short_but_nonempty_passes():
    f = make_file({"TEXT": attr("TEXT", ["Short text."])})
    rule = load_rule("GlobalAttributes", "TextNotEmpty")
    assert rule.check(f).valid


def test_fillval_range_check_exempts_time_types():
    """CDF time variables use a standardized FILLVAL and tt2000_t is not ordered,
    so the [VALIDMIN, VALIDMAX] range check must not fire on them."""
    f = make_file(
        variables={
            "Epoch": var(
                "Epoch",
                "support_data",
                {
                    # FILLVAL deliberately *inside* [VALIDMIN, VALIDMAX]: would fail
                    # for a numeric variable, but time types are exempt.
                    "FILLVAL": attr("FILLVAL", [50], DataType.TT2000),
                    "VALIDMIN": attr("VALIDMIN", [0], DataType.TT2000),
                    "VALIDMAX": attr("VALIDMAX", [100], DataType.TT2000),
                },
                data_type=DataType.TT2000,
            )
        }
    )
    rule = load_rule("VariableAttributes", "FillvalOutsideRange")
    assert rule.check(f).valid


def test_fillval_range_check_skipped_without_bounds():
    """When VALIDMIN/VALIDMAX are absent the range is undefined, so the check must
    be skipped rather than reporting a 'comparison target not found' false error."""
    f = make_file(
        variables={
            "B": var(
                "B",
                "data",
                {"FILLVAL": attr("FILLVAL", [-1e31], DataType.FLOAT64)},  # no VALIDMIN/MAX
            )
        }
    )
    rule = load_rule("VariableAttributes", "FillvalOutsideRange")
    assert rule.check(f).valid


def test_fillval_nan_is_allowed():
    f = make_file(
        variables={
            "B": var(
                "B",
                "data",
                {
                    "FILLVAL": attr("FILLVAL", [float("nan")], DataType.FLOAT64),
                    "VALIDMIN": attr("VALIDMIN", [0.0], DataType.FLOAT64),
                    "VALIDMAX": attr("VALIDMAX", [100.0], DataType.FLOAT64),
                },
            )
        }
    )
    rule = load_rule("VariableAttributes", "FillvalOutsideRange")
    assert rule.check(f).valid


def test_fillval_nan_allowed_through_real_cdf_roundtrip():
    """Regression: a NaN FILLVAL must pass VA-019 after a real CDF round-trip.

    The codec loads numeric variable attributes nested (FILLVAL -> ``values/0``
    is the 1-element list ``[nan]``, not the scalar ``nan``). That turned the
    ``FILLVAL != FILLVAL`` NaN clause into a list comparison, and ``[nan] != [nan]``
    is False (list equality short-circuits on element identity), so NaN was wrongly
    flagged as inside the range. The flat-``values`` unit test above never produced
    that shape, so it masked the bug; this one exercises the true codec output."""
    import numpy as np
    import pycdfpp

    from astralint.codecs.cdf import CdfCodec

    src = Path(__file__).parent / "resources" / "mms1_asp2_srvy_l1b_stat_00000000_v01.cdf"
    cdf = pycdfpp.load(str(src))
    target = next(
        name for name, v in cdf.items() if v.type == pycdfpp.DataType.CDF_REAL4 and not v.is_nrv
    )
    for key, value in (("VALIDMIN", 0.0), ("VALIDMAX", 100.0), ("FILLVAL", float("nan"))):
        arr = np.array([value], dtype=np.float32)
        if key in cdf[target].attributes:
            cdf[target].attributes[key].set_value(arr, pycdfpp.DataType.CDF_FLOAT)
        else:
            cdf[target].add_attribute(key, arr, pycdfpp.DataType.CDF_FLOAT)

    loaded = CdfCodec.load(bytes(pycdfpp.save(cdf)))
    assert loaded is not None
    # the bug condition: values/0 is a nested list, not a scalar
    assert isinstance(loaded.variables[target].attributes["FILLVAL"].values[0], list)

    # isolate the target variable so an unrelated pre-existing finding
    # (mms1_asp_stat's full-range UINT1 FILLVAL) doesn't mask the result
    only_target = loaded.model_copy(update={"variables": {target: loaded.variables[target]}})
    rule = load_rule("VariableAttributes", "FillvalOutsideRange")
    assert rule.check(only_target).valid


# --- Hard-vs-soft: CDAWeb-required globals ------------------------------------


def _istp_required_globals() -> dict:
    return {
        k: attr(k, [v])
        for k, v in {
            "Data_type": "L2>Level 2",
            "Data_version": "1",
            "Descriptor": "ABC>A B C",
            "Logical_file_id": "a_b_c_20200101_v01",
            "Logical_source": "a_b_c",
            "Logical_source_description": "desc",
            "PI_affiliation": "Org",
            "PI_name": "J. Doe",
            "Source_name": "ABC>A B C",
            "TEXT": "A long enough description of the data.",
        }.items()
    }


def test_mandatory_globals_no_longer_require_cdaweb_attrs():
    """Instrument_type and Mission_group are CDAWeb-required, not ISTP-mandatory."""
    f = make_file(_istp_required_globals())
    rule = load_rule("GlobalAttributes", "MandatoryGlobalAttributes")
    assert rule.check(f).valid


def test_cdaweb_required_rule_flags_missing_attrs():
    f = make_file(_istp_required_globals())
    rule = load_rule("GlobalAttributes", "CDAWebRequiredGlobalAttributes")
    assert not rule.check(f).valid
    assert rule.severity.value == "WARNING"


def test_recommended_globals_include_file_naming_convention():
    src = (RULES_DIR / "GlobalAttributes" / "RecommendedGlobalAttributes.yaml").read_text()
    assert "File_naming_convention" in src


# --- Epoch rules are name-agnostic (key on CDF time data type, not name) -----


def test_epoch_variable_accepts_non_epoch_named_time_var():
    """A CDF time variable under any name satisfies the epoch requirement."""
    f = make_file(
        variables={
            "mms1_asp_epoch": var(
                "mms1_asp_epoch",
                "support_data",
                {"CATDESC": attr("CATDESC", ["Time"]), "FIELDNAM": attr("FIELDNAM", ["Epoch"])},
                data_type=DataType.TT2000,
            )
        }
    )
    rule = load_rule("Variables", "EpochVariable")
    assert rule.check(f).valid


def test_epoch_variable_missing_time_var_fails():
    f = make_file(variables={"B": var("B", "data", data_type=DataType.FLOAT64)})
    rule = load_rule("Variables", "EpochVariable")
    assert not rule.check(f).valid


def test_epoch_attributes_apply_to_any_time_var_regardless_of_name():
    """A time variable with the wrong VAR_TYPE is flagged even if not named Epoch."""
    f = make_file(
        variables={
            "time": var(
                "time",
                "data",  # wrong: an epoch/time variable should be support_data
                {"CATDESC": attr("CATDESC", ["t"]), "FIELDNAM": attr("FIELDNAM", ["t"])},
                data_type=DataType.TT2000,
            )
        }
    )
    rule = load_rule("Variables", "EpochAttributes")
    assert not rule.check(f).valid


def test_epoch_recommended_tt2000_does_not_require_time_base():
    """TIME_BASE/TIME_SCALE are not needed for CDF_TIME_TT2000."""
    f = make_file(
        variables={
            "tt": var(
                "tt",
                "support_data",
                {"MONOTON": attr("MONOTON", ["INCREASE"])},
                data_type=DataType.TT2000,
            )
        }
    )
    rule = load_rule("Variables", "EpochRecommendedAttributes")
    assert rule.check(f).valid


# --- any_match existential semantics -----------------------------------------


def test_any_match_fails_on_zero_matches_even_when_lenient():
    """An existential quantifier must fail when nothing matches, regardless of a
    lenient error_if_no_match on the wrapped assertion."""
    from astralint.base.validation_result import Severity
    from astralint.base.yaml_rules.assertions.combinations import AnyMatch

    f = make_file(variables={"B": var("B", "data")})
    am = AnyMatch.model_validate(
        {
            "check": "any_match",
            "assertion": {
                "path": "variables/Nonexistent/data_type",
                "check": "in",
                "values": ["TT2000"],
                "error_if_no_match": False,
            },
        }
    )
    assert not am.evaluate(f, Severity.ERROR).valid


# --- URLs point to the ReadTheDocs guidelines --------------------------------


def test_all_rule_urls_point_to_readthedocs():
    bad = []
    for path in RULES_DIR.rglob("*.yaml"):
        rule = load_yaml_rule(path)
        if not rule.url.startswith("https://istp-metadata.readthedocs.io/"):
            bad.append(path.name)
    assert not bad, f"rules with non-RTD url: {bad}"
