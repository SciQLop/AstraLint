from .models import ApplyPolicy, ReferenceSource, ResolverEntry, Scope
from .sources.filename import (
    data_version_from_filename,
    logical_file_id_from_filename,
    logical_source_from_filename,
)
from .sources.graph_rules import depend0_finder, display_type_infer, var_type_infer
from .sources.pointers import dangling_pointer_suggestion
from .sources.type_rules import fillval_by_type, scaletyp_default

# Rule references that flag a dangling pointer for each pointer family.
_POINTER_TRIGGERS = {
    "DEPEND_0": ["ISTP-VA-011"],
    "DEPEND_1": ["ISTP-VA-011"],
    "DEPEND_2": ["ISTP-VA-011"],
    "DEPEND_3": ["ISTP-VA-011"],
    "LABL_PTR_1": ["ISTP-VA-012"],
    "LABL_PTR_2": ["ISTP-VA-012"],
    "LABL_PTR_3": ["ISTP-VA-012"],
    "UNIT_PTR": ["ISTP-VA-016"],
    "FORM_PTR": ["ISTP-VA-017"],
    "SCAL_PTR": ["ISTP-VA-018"],
    "DELTA_PLUS_VAR": ["ISTP-VA-014"],
    "DELTA_MINUS_VAR": ["ISTP-VA-014"],
}


def _pointer_entry(attribute: str, triggers: list[str]) -> ResolverEntry:
    return ResolverEntry(
        attribute=attribute,
        scope=Scope.VARIABLE,
        sources=[ReferenceSource.GRAPH_RULE],
        resolver=dangling_pointer_suggestion,
        auto_apply=ApplyPolicy.NEVER,
        confidence_default=0.5,
        triggers=triggers,
    )


REGISTRY: list[ResolverEntry] = [
    ResolverEntry(
        attribute="FILLVAL",
        scope=Scope.VARIABLE,
        sources=[ReferenceSource.TYPE_RULE],
        resolver=fillval_by_type,
        auto_apply=ApplyPolicy.ALWAYS,
        confidence_default=1.0,
        triggers=["ISTP-VA-001"],
    ),
    ResolverEntry(
        attribute="SCALETYP",
        scope=Scope.VARIABLE,
        sources=[ReferenceSource.TYPE_RULE],
        resolver=scaletyp_default,
        auto_apply=ApplyPolicy.ALWAYS,
        confidence_default=1.0,
        triggers=["ISTP-VA-013"],
    ),
    ResolverEntry(
        attribute="VAR_TYPE",
        scope=Scope.VARIABLE,
        sources=[ReferenceSource.GRAPH_RULE],
        resolver=var_type_infer,
        auto_apply=ApplyPolicy.IF_UNIQUE,
        confidence_default=0.9,
        triggers=["ISTP-VA-001", "ISTP-VA-004"],
    ),
    ResolverEntry(
        attribute="DEPEND_0",
        scope=Scope.VARIABLE,
        sources=[ReferenceSource.GRAPH_RULE],
        resolver=depend0_finder,
        auto_apply=ApplyPolicy.IF_UNIQUE,
        confidence_default=0.8,
        triggers=["ISTP-VA-002"],
    ),
    ResolverEntry(
        attribute="DISPLAY_TYPE",
        scope=Scope.VARIABLE,
        sources=[ReferenceSource.GRAPH_RULE],
        resolver=display_type_infer,
        auto_apply=ApplyPolicy.IF_UNIQUE,
        confidence_default=0.8,
        triggers=["ISTP-VA-002", "ISTP-VA-005"],
    ),
    # Filename-derived global attributes (AUTO when the filename matches the
    # ISTP convention; the resolver returns None otherwise). Triggers cover both
    # the malformed-value rule and the missing-attribute rule (ISTP-GA-001).
    ResolverEntry(
        attribute="Logical_file_id",
        scope=Scope.GLOBAL,
        sources=[ReferenceSource.FILENAME],
        resolver=logical_file_id_from_filename,
        auto_apply=ApplyPolicy.ALWAYS,
        confidence_default=0.9,
        triggers=["ISTP-GA-004", "ISTP-GA-001"],
    ),
    ResolverEntry(
        attribute="Logical_source",
        scope=Scope.GLOBAL,
        sources=[ReferenceSource.FILENAME],
        resolver=logical_source_from_filename,
        auto_apply=ApplyPolicy.ALWAYS,
        confidence_default=0.9,
        triggers=["ISTP-GA-003", "ISTP-GA-001"],
    ),
    ResolverEntry(
        attribute="Data_version",
        scope=Scope.GLOBAL,
        sources=[ReferenceSource.FILENAME],
        resolver=data_version_from_filename,
        auto_apply=ApplyPolicy.ALWAYS,
        confidence_default=0.9,
        triggers=["ISTP-GA-005", "ISTP-GA-001"],
    ),
    *[_pointer_entry(attr, triggers) for attr, triggers in _POINTER_TRIGGERS.items()],
]
