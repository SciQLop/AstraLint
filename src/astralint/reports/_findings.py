"""Shared presentation logic for the console and HTML reporters.

Turns a rule's raw result tree into the flat list of *display* items: internal
per-assertion wrapper groups are flattened away, each leaf is stamped with the
nearest enclosing rule reference, and pass-path noise leaves (skipped conditions,
optional-absent attributes) are dropped. Real groupings — rule groups and
per-file/suite groups — are preserved so the renderers keep their structure.
"""

from ..base import Severity, ValidationResult, ValidationResultGroup

# Mirrors the valid branch of `_NO_MATCH_TEMPLATE` in
# base/yaml_rules/assertions/base.py and compare_to.py. These leaves mean
# "the optional attribute is absent", not "a member is valid".
_NOT_REQUIRED_MARKER = "did not match any values (not required)"


def is_internal_wrapper(group: ValidationResultGroup) -> bool:
    """A per-assertion ``…Assertion``/``all_of``/``IfThen`` wrapper, as opposed to a
    rule group (has a ``rule_reference``) or a per-file/suite group (has a ``message``
    and/or ``url``). Only wrappers are flattened away."""
    return not group.rule_reference and not group.message and not group.url


def _is_pass_noise(leaf: ValidationResult) -> bool:
    """A passing leaf that carries no information about a validated member."""
    if leaf.severity == Severity.SKIPPED:
        return True
    return leaf.valid and _NOT_REQUIRED_MARKER in leaf.message


def display_children(
    group: ValidationResultGroup, reference: str = ""
) -> list[ValidationResult | ValidationResultGroup]:
    """Items to render directly under ``group``: wrappers flattened, leaves stamped
    with the nearest rule reference, pass-path noise dropped. Non-wrapper subgroups
    are returned as-is for the renderer to recurse into."""
    reference = group.rule_reference or reference
    items: list[ValidationResult | ValidationResultGroup] = []
    for child in group.results:
        if isinstance(child, ValidationResultGroup):
            if is_internal_wrapper(child):
                items.extend(display_children(child, reference))
            else:
                items.append(child)
        elif not _is_pass_noise(child):
            items.append(
                child if child.reference else child.model_copy(update={"reference": reference})
            )
    return items
