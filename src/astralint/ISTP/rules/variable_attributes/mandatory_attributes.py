import pycdfpp

from ....base import Rule, ValidationResult, Severity
from ..istp_rules import register_istp_rule


@register_istp_rule
class MandatoryVariablesAttributes(Rule):
    @property
    def description(self) -> str:
        return "All global attributes must be present."

    @property
    def url(self) -> str:
        return "https://github.com/IHDE-Alliance/ISTP_metadata/blob/main/ISTP_metadata_guidelines/docs/05_metadata-variable-attributes.md#istp-variable-attributes"

    @property
    def reference(self) -> str:
        return "ISTP-MD-002"

    @property
    def name(self) -> str:
        return "Mandatory Global Attributes"

    @property
    def severity(self) -> Severity:
        return Severity.ERROR

    def check(self, file) -> list[ValidationResult]:
        required_attributes = {
            "CATDESC",
            "DEPEND_0",
            "DISPLAY_TYPE"
        }
        results = []
        cdf = pycdfpp.load(file)
        for name, var in cdf.items():
            missing_attributes = required_attributes - set(var.attributes.keys())
            if missing_attributes:
                for attr in missing_attributes:
                    results.append(self._format_result(
                        valid=False,
                        message=f"Missing mandatory variable attribute '{attr}' in variable '{name}'"
                    ))
            else:
                results.append(self._format_result(
                    valid=True,
                    message=f"All mandatory global attributes are present in variable '{name}'."
                ))
        return results
