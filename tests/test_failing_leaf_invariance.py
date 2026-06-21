# tests/test_failing_leaf_invariance.py
from astralint.base import ValidationResult, ValidationResultGroup, get_suite, load_file

RESOURCE = "tests/resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf"


def _leaves(node):
    if isinstance(node, ValidationResult):
        yield node
    else:
        for child in node.results:
            yield from _leaves(child)


def _failing_signature(node) -> list[tuple[str, str, str, str]]:
    return sorted(
        (leaf.reference, leaf.target, leaf.severity.value, leaf.message)
        for leaf in _leaves(node)
        if not leaf.valid
    )


EXPECTED: list[tuple[str, str, str, str]] = [
    ("", "", "ERROR", "Data variable must have UNITS or UNIT_PTR"),
    ("", "", "INFO", "PROPOSAL: Data_processing_level attribute is available"),
    ("", "", "WARNING", "missing recommended global attribute(s): DOI, spase_DatasetResourceID"),
    ("", "Instrument_type", "WARNING", "Instrument_type should use a standard ISTP value"),
    ("", "label_stat", "INFO", "Attribute COORDINATE_SYSTEM of label_stat is available for vectors/tensors (proposal)"),
    ("", "label_stat/LABLAXIS", "WARNING", "Attribute LABLAXIS of label_stat (length 12) should be 10 characters or less"),
    ("", "mms1_asp_epoch", "ERROR", "mms1_asp_epoch missing required attribute(s): DEPEND_0"),
    ("", "mms1_asp_epoch", "INFO", "Attribute COORDINATE_SYSTEM of mms1_asp_epoch is available for vectors/tensors (proposal)"),
    ("", "mms1_asp_epoch/VAR_TYPE", "ERROR", "time variable mms1_asp_epoch should have VAR_TYPE='support_data' (got 'data')"),
    ("", "mms1_asp_n120v", "INFO", "Attribute COORDINATE_SYSTEM of mms1_asp_n120v is available for vectors/tensors (proposal)"),
    ("", "mms1_asp_p015v", "INFO", "Attribute COORDINATE_SYSTEM of mms1_asp_p015v is available for vectors/tensors (proposal)"),
    ("", "mms1_asp_p033v", "INFO", "Attribute COORDINATE_SYSTEM of mms1_asp_p033v is available for vectors/tensors (proposal)"),
    ("", "mms1_asp_p050v", "INFO", "Attribute COORDINATE_SYSTEM of mms1_asp_p050v is available for vectors/tensors (proposal)"),
    ("", "mms1_asp_p120v", "INFO", "Attribute COORDINATE_SYSTEM of mms1_asp_p120v is available for vectors/tensors (proposal)"),
    ("", "mms1_asp_stat", "INFO", "Attribute COORDINATE_SYSTEM of mms1_asp_stat is available for vectors/tensors (proposal)"),
    ("", "mms1_asp_stat/FILLVAL", "ERROR", "Attribute FILLVAL of mms1_asp_stat must be outside [VALIDMIN, VALIDMAX] range (or NaN)"),
    ("", "mms1_asp_tbox", "INFO", "Attribute COORDINATE_SYSTEM of mms1_asp_tbox is available for vectors/tensors (proposal)"),
    ("", "mms1_asp_tdcc", "INFO", "Attribute COORDINATE_SYSTEM of mms1_asp_tdcc is available for vectors/tensors (proposal)"),
    ("", "mms1_asp_tdpu", "INFO", "Attribute COORDINATE_SYSTEM of mms1_asp_tdpu is available for vectors/tensors (proposal)"),
    ("", "mms1_asp_tmod", "INFO", "Attribute COORDINATE_SYSTEM of mms1_asp_tmod is available for vectors/tensors (proposal)"),
]


def test_failing_leaves_are_unchanged():
    """The resolver routes on failing-leaf (reference, target, message); this work
    must not change any failing-path output. If this breaks, a pass-path change
    leaked into the failure path."""
    results = get_suite("ISTP").run(load_file(RESOURCE))
    assert _failing_signature(results) == EXPECTED
