from astralint.resolver.models import ApplyPolicy, ReferenceSource
from astralint.resolver.registry import REGISTRY


def test_registry_has_fillval_entry():
    fillval = [e for e in REGISTRY if e.attribute == "FILLVAL"]
    assert len(fillval) == 1
    assert fillval[0].auto_apply == ApplyPolicy.ALWAYS
    assert fillval[0].sources == [ReferenceSource.TYPE_RULE]
    assert "ISTP-VA-001" in fillval[0].triggers


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
