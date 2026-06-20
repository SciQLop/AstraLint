from astralint.base.file import Attribute, DataType, File, Variable
from astralint.base.validation_result import (
    Severity,
    ValidationResult,
    ValidationResultGroup,
)
from astralint.resolver.engine import resolve


def _attr(name, value, dt=DataType.CHAR):
    return Attribute(name=name, data_type=[dt], shape=[1], values=[value])


def _file():
    return File(
        extension="cdf",
        filename="t.cdf",
        compression="NONE",
        attributes={},
        variables={
            "Epoch": Variable(
                name="Epoch",
                shape=[10],
                attributes={"VAR_TYPE": _attr("VAR_TYPE", "support_data")},
                compression="NONE",
                data_type=DataType.TT2000,
                record_variance=True,
            ),
            "flux": Variable(
                name="flux",
                shape=[10],
                attributes={},
                compression="NONE",
                data_type=DataType.FLOAT32,
                record_variance=True,
            ),
        },
    )


def _failure(reference, target, value=""):
    return ValidationResult(
        valid=False,
        reference=reference,
        severity=Severity.ERROR,
        message="boom",
        target=target,
        value=value,
    )


def _group(results):
    return ValidationResultGroup(
        name="g", rule_reference="", severity=Severity.ERROR, results=results
    )


def test_resolve_fillval_missing_on_record_varying_var():
    # ISTP-VA-001 missing-mandatory failure on variable "flux"; target is the var.
    failures = _group([_failure("ISTP-VA-001", "flux")])
    fixes = resolve(_file(), failures)
    fillval = [f for f in fixes if f.attribute == "FILLVAL"]
    assert len(fillval) == 1
    assert fillval[0].value == -1e31
    assert fillval[0].action == "add"
    assert fillval[0].auto is True
    assert fillval[0].target_path == "variables/flux/attributes/FILLVAL"


def test_resolve_depend0_finder_on_data_var_attributes_failure():
    failures = _group([_failure("ISTP-VA-002", "flux")])
    fixes = resolve(_file(), failures)
    depend0 = [f for f in fixes if f.attribute == "DEPEND_0"]
    assert len(depend0) == 1
    assert depend0[0].value == "Epoch"
    assert depend0[0].auto is True  # unique


def test_resolve_dangling_depend0_is_staged_not_auto():
    f = _file()
    f.variables["flux"].attributes["DEPEND_0"] = _attr("DEPEND_0", "Epokh")
    failures = _group([_failure("ISTP-VA-011", "flux/DEPEND_0", value="Epokh")])
    fixes = resolve(f, failures)
    dangling = [x for x in fixes if x.attribute == "DEPEND_0"]
    assert len(dangling) == 1
    assert dangling[0].value == "Epoch"
    assert dangling[0].auto is False  # NEVER auto-applied
    assert dangling[0].action == "set"


def test_resolve_dedups_same_target():
    # Two failures that both route to FILLVAL on the same variable.
    failures = _group([_failure("ISTP-VA-001", "flux"), _failure("ISTP-VA-001", "flux")])
    fixes = resolve(_file(), failures)
    assert len([f for f in fixes if f.attribute == "FILLVAL"]) == 1


def test_resolve_reads_reference_from_enclosing_rule_group():
    # Real validation output puts the rule reference on the enclosing rule
    # group's `rule_reference`, NOT on the leaf (the leaf's own `reference` is
    # empty). The engine must use the enclosing rule reference for trigger
    # matching — otherwise it resolves nothing on real files.
    leaf = ValidationResult(
        valid=False,
        reference="",  # empty, as real leaves are
        severity=Severity.ERROR,
        message="missing mandatory attributes",
        target="flux",
        value="",
    )
    rule_group = ValidationResultGroup(
        name="MandatoryVariableAttributes",
        rule_reference="ISTP-VA-001",  # the reference lives here
        severity=Severity.ERROR,
        results=[leaf],
    )
    top = ValidationResultGroup(
        name="results", rule_reference="", severity=Severity.ERROR, results=[rule_group]
    )
    fixes = resolve(_file(), top)
    assert any(f.attribute == "FILLVAL" and f.auto for f in fixes)
