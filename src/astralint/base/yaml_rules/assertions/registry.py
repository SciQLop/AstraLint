from typing import Union, Annotated
from pydantic import Field
from .base import BaseAssertion
from ....logger import get_logger

# Registry of all assertion types
ASSERTION_TYPES: dict[str, type[BaseAssertion]] = {}

log = get_logger(__name__)


def register_assertion(cls: type[BaseAssertion]) -> type[BaseAssertion]:
    """Decorator to register new assertion types."""
    check_field = cls.model_fields.get("check")
    if check_field and check_field.default:
        ASSERTION_TYPES[check_field.default] = cls
        log.debug(f"Registered assertion type: {check_field.default} -> {cls.__name__}")
    return cls


def get_assertion_union():
    """Build discriminated union from registered types."""
    types = tuple(ASSERTION_TYPES.values())
    return Annotated[Union[types], Field(discriminator="check")]
