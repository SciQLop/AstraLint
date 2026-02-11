from astralint.base import build_suite
from pycdfpp import load
from  .rules.istp_rules import ISTP_RULES

ISTP = build_suite(description="", url="", rules=ISTP_RULES)
