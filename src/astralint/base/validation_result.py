from enum import Enum
from dataclasses import dataclass


class Severity(Enum):
    ERROR = "ERROR"      # Mandatory ISTP requirement
    WARNING = "WARNING"  # Recommended practice
    INFO = "INFO"        # Optional or metadata info

@dataclass
class ValidationResult:
    valid: bool
    reference: str
    severity: Severity
    message: str
    target: str = "Global"