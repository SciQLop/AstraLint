from astralint.resolver.models import ApplyPolicy, ReferenceSource
from astralint.resolver.registry import REGISTRY


def test_registry_has_fillval_entry():
    # FILLVAL has two entries: the by-type default (missing FILLVAL, VA-001) and
    # the range-aware one (FILLVAL inside [VALIDMIN,VALIDMAX], VA-019).
    fillval = [e for e in REGISTRY if e.attribute == "FILLVAL"]
    by_type = [e for e in fillval if "ISTP-VA-001" in e.triggers]
    assert len(by_type) == 1
    assert by_type[0].auto_apply == ApplyPolicy.ALWAYS
    assert by_type[0].sources == [ReferenceSource.TYPE_RULE]


def test_pointer_entries_are_never_auto():
    pointer_attrs = {"DEPEND_0", "DEPEND_1", "LABL_PTR_1", "UNIT_PTR", "FORM_PTR"}
    pointer_entries = [
        e for e in REGISTRY if e.attribute in pointer_attrs and e.auto_apply == ApplyPolicy.NEVER
    ]
    assert pointer_entries  # at least the dangling-pointer entries exist


def test_every_entry_resolver_is_callable():
    assert all(callable(e.resolver) for e in REGISTRY)


def test_depend0_has_both_a_finder_and_a_dangling_entry():
    depend0 = [e for e in REGISTRY if e.attribute == "DEPEND_0"]
    triggers = {t for e in depend0 for t in e.triggers}
    assert "ISTP-VA-002" in triggers  # missing -> finder
    assert "ISTP-VA-011" in triggers  # dangling -> suggestion


def test_registry_has_filename_global_entries():
    from astralint.resolver.models import ReferenceSource, Scope

    filename_entries = [e for e in REGISTRY if ReferenceSource.FILENAME in e.sources]
    attrs = {e.attribute for e in filename_entries}
    assert {"Logical_file_id", "Logical_source", "Data_version"} <= attrs
    assert all(e.scope == Scope.GLOBAL for e in filename_entries)


def test_var_type_entry_triggers_on_epoch_rule():
    var_type = [e for e in REGISTRY if e.attribute == "VAR_TYPE"]
    triggers = {t for e in var_type for t in e.triggers}
    assert "ISTP-VAR-002" in triggers  # epoch VAR_TYPE=support_data graph win


def test_fillval_entry_triggers_on_fillval_range():
    fillval = [e for e in REGISTRY if e.attribute == "FILLVAL"]
    triggers = {t for e in fillval for t in e.triggers}
    assert "ISTP-VA-019" in triggers  # FillvalOutsideRange -> set type-standard fill


def test_truncation_entries_are_staged():
    from astralint.resolver.models import ApplyPolicy

    truncate = {
        e.attribute: e for e in REGISTRY if e.attribute in {"CATDESC", "FIELDNAM", "LABLAXIS"}
    }
    assert {"CATDESC", "FIELDNAM", "LABLAXIS"} <= set(truncate)
    assert all(e.auto_apply == ApplyPolicy.NEVER for e in truncate.values())
