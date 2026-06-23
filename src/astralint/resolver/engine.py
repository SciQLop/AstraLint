from ..base.file import File
from ..base.validation_result import Severity, ValidationResultGroup
from .models import ApplyPolicy, Fix, ReferenceSource, ResolverEntry, ResolverOutput, Scope
from .registry import REGISTRY

# PDS4/CDF-A structural failures all cleared by one lossless re-save (store the CDF
# uncompressed; pycdfpp.save also writes variables contiguously).
_NORMALIZE_TRIGGERS = {"PDS4-CDFA-001", "PDS4-CDFA-002", "PDS4-CDFA-004"}


def _iter_failures(group: ValidationResultGroup, inherited_reference: str = ""):
    """Yield (rule_reference, failing_leaf) pairs.

    The rule reference (e.g. "ISTP-VA-004") lives on the enclosing rule's
    ``ValidationResultGroup.rule_reference``, not on the leaf — a leaf's own
    ``reference`` is usually empty. Carry the nearest non-empty rule reference
    down to each leaf so the registry can match it against entry triggers.
    """
    reference = group.rule_reference or inherited_reference
    for result in group.results:
        if isinstance(result, ValidationResultGroup):
            yield from _iter_failures(result, reference)
        elif not result.valid and result.severity != Severity.SKIPPED:
            yield result.reference or reference, result


def _split_target(file: File, target: str) -> tuple[str | None, str | None, Scope]:
    """Derive (variable, attribute, scope) from a ValidationResult.target.

    Formats produced by clean_target:
      "var/attr" -> variable + attribute
      "token"    -> a variable (attribute unknown) or a global attribute
      ""         -> global, no attribute
    """
    if not target:
        return None, None, Scope.GLOBAL
    if "/" in target:
        variable, attribute = target.split("/", 1)
        return variable, attribute, Scope.VARIABLE
    if target in file.variables:
        return target, None, Scope.VARIABLE
    return None, target, Scope.GLOBAL


def _entry_matches(
    entry: ResolverEntry, reference: str, attribute: str | None, scope: Scope
) -> bool:
    if entry.scope != scope:
        return False
    if entry.triggers and reference not in entry.triggers:
        return False
    if attribute is not None and entry.attribute != attribute:
        return False
    return True


def _attribute_present(file: File, entry: ResolverEntry, variable: str | None) -> bool:
    if entry.scope == Scope.VARIABLE and variable is not None:
        return entry.attribute in file.variables[variable].attributes
    return entry.attribute in file.attributes


def _build_fix(
    file: File, entry: ResolverEntry, variable: str | None, output: ResolverOutput
) -> Fix:
    attribute = entry.attribute
    if entry.scope == Scope.VARIABLE and variable is not None:
        present = attribute in file.variables[variable].attributes
        target_path = f"variables/{variable}/attributes/{attribute}"
    else:
        present = attribute in file.attributes
        target_path = f"attributes/{attribute}"
    auto = entry.auto_apply == ApplyPolicy.ALWAYS or (
        entry.auto_apply == ApplyPolicy.IF_UNIQUE and not output.ambiguous
    )
    return Fix(
        target_path=target_path,
        variable=variable,
        attribute=attribute,
        scope=entry.scope,
        action="set" if present else "add",
        value=output.value,
        source=entry.sources[0],
        confidence=output.confidence if output.confidence is not None else entry.confidence_default,
        provenance_note=output.provenance_note,
        auto=auto,
    )


def _structural_fix(failures: ValidationResultGroup) -> list[Fix]:
    """A single lossless re-save that clears compression (CDFA-001/002) and
    fragmentation (CDFA-004). Emitted once when any of those rules fail."""
    references = {reference for reference, _ in _iter_failures(failures)}
    if not references & _NORMALIZE_TRIGGERS:
        return []
    return [
        Fix(
            target_path="compression",
            variable=None,
            attribute="compression",
            scope=Scope.GLOBAL,
            action="normalize",
            value="no_compression",
            source=ReferenceSource.STRUCTURE,
            confidence=1.0,
            provenance_note="store the CDF uncompressed and contiguous (PDS4/CDF-A); lossless re-save",
            auto=True,
        )
    ]


def resolve(file: File, failures: ValidationResultGroup) -> list[Fix]:
    fixes: dict[str, Fix] = {}  # keyed on target_path for dedup
    for reference, leaf in _iter_failures(failures):
        variable, attribute, scope = _split_target(file, leaf.target)
        for entry in REGISTRY:
            if not _entry_matches(entry, reference, attribute, scope):
                continue
            # When the failure does not name a specific attribute (its target is
            # just the variable, e.g. a "missing required attribute(s)" failure),
            # only fill genuinely-absent attributes — never overwrite an existing
            # attribute the failure never flagged.
            if attribute is None and _attribute_present(file, entry, variable):
                continue
            output = entry.resolver(file, variable, entry.attribute, leaf)
            if output is None:
                continue
            fix = _build_fix(file, entry, variable, output)
            existing = fixes.get(fix.target_path)
            if existing is None or fix.confidence > existing.confidence:
                fixes[fix.target_path] = fix
    return list(fixes.values()) + _structural_fix(failures)
