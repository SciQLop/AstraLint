import pycdfpp

from ....base import Rule, ValidationResult, Severity
from ..istp_rules import register_istp_rule


@register_istp_rule
class MandatoryAttributes(Rule):
    @property
    def description(self) -> str:
        return "All global attributes must be present."

    @property
    def url(self) -> str:
        return "https://github.com/IHDE-Alliance/ISTP_metadata/blob/main/ISTP_metadata_guidelines/docs/03_metadata-global-attributes.md#istp-global-attributes"

    @property
    def reference(self) -> str:
        return "ISTP-MD-001"

    @property
    def name(self) -> str:
        return "Mandatory Global Attributes"

    @property
    def severity(self) -> Severity:
        return Severity.ERROR

    def check(self, file) -> list[ValidationResult]:
        required_attributes = {
            "Data_type",
            "Data_version",
            "Descriptor",
            "Instrument_type",
            "Logical_file_id",
            "Logical_source",
            "Logical_source_description",
            "Mission_group",
            "PI_affiliation",
            "PI_name",
            "Source_name",
            "TEXT"
        }
        results = []
        cdf = pycdfpp.load(file)
        missing_attributes = required_attributes - set(cdf.attributes.keys())
        if missing_attributes:
            for attr in missing_attributes:
                results.append(self._format_result(
                    valid=False,
                    message=f"Missing mandatory global attribute: {attr}"
                ))
        else:
            results.append(self._format_result(
                valid=True,
                message="All mandatory global attributes are present."
            ))
        return results
