from astralint.base.file import Attribute, DataType, File
from astralint.resolver.models import Fix, ReferenceSource, Scope
from astralint.resolver.sources.user import needs_user_input


def _global(attr_name: str) -> File:
    return File(
        extension="cdf",
        filename="t.cdf",
        compression="NONE",
        variables={},
        attributes={
            attr_name: Attribute(name=attr_name, data_type=[DataType.CHAR], shape=[1], values=[""])
        },
    )


def test_needs_user_input_flags_without_value():
    out = needs_user_input(_global("DOI"), None, "DOI", None)
    assert out is not None
    assert out.value is None
    assert "DOI" in out.provenance_note


def _fix(source: ReferenceSource, *, auto: bool, value) -> Fix:
    return Fix(
        target_path="attributes/X",
        variable=None,
        attribute="X",
        scope=Scope.GLOBAL,
        action="add",
        value=value,
        source=source,
        confidence=0.0,
        provenance_note="n",
        auto=auto,
    )


def test_fix_disposition():
    assert _fix(ReferenceSource.TYPE_RULE, auto=True, value=1).disposition == "auto"
    assert _fix(ReferenceSource.FORMAT_RULE, auto=False, value="x").disposition == "staged"
    assert _fix(ReferenceSource.USER, auto=False, value=None).disposition == "user"
