from astralint.resolver.models import (
    ApplyPolicy,
    Fix,
    ReferenceSource,
    ResolverEntry,
    ResolverOutput,
    Scope,
)


def test_resolver_output_defaults():
    out = ResolverOutput(value=-1e31, provenance_note="default")
    assert out.confidence is None
    assert out.ambiguous is False
    assert out.alternatives == []


def test_resolver_entry_holds_callable():
    def dummy(file, variable, attribute, failure):
        return None

    entry = ResolverEntry(
        attribute="FILLVAL",
        scope=Scope.VARIABLE,
        sources=[ReferenceSource.TYPE_RULE],
        resolver=dummy,
        auto_apply=ApplyPolicy.ALWAYS,
        confidence_default=1.0,
    )
    assert entry.triggers == []
    assert entry.resolver is dummy


def test_fix_is_auditable():
    fix = Fix(
        target_path="variables/Epoch/attributes/FILLVAL",
        variable="Epoch",
        attribute="FILLVAL",
        scope=Scope.VARIABLE,
        action="add",
        value=-1e31,
        source=ReferenceSource.TYPE_RULE,
        confidence=1.0,
        provenance_note="ISTP default",
        auto=True,
    )
    assert fix.source == ReferenceSource.TYPE_RULE
    assert fix.confidence == 1.0
    assert fix.provenance_note
