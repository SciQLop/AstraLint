from astralint.base import File, RegisterRule, Rule, Severity, ValidationResult, ValidationResultGroup


@RegisterRule(suite="ISTP")
class MandatoryVariablesAttributes(Rule):
    name: str = "Mandatory Global Attributes"
    description: str = "Mandatory Global Attributes"
    url: str = "https://github.com/IHDE-Alliance/ISTP_metadata/blob/main/ISTP_metadata_guidelines/docs/05_metadata-variable-attributes.md#istp-variable-attributes"
    reference: str = "ISTP-MD-002"
    severity: Severity = Severity.ERROR

    def check(self, file: File) -> ValidationResult | ValidationResultGroup:
        required_attributes = {
            "CATDESC",
            "DEPEND_0",
            "DISPLAY_TYPE"
        }
        results = []
        for name, var in file.variables.items():
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
        return ValidationResultGroup(
            name=self.name,
            rule_reference=self.reference,
            results=results,
            severity=self.severity,
        )
