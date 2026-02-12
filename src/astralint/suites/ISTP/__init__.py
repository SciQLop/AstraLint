from astralint.base import register_suite
import os

__HERE__ = os.path.dirname(__file__)


register_suite(description="",url="", rules_lookup_dir=os.path.join(__HERE__, "rules"),name="ISTP")