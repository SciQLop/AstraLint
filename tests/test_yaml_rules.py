import os

from astralint.base.yaml_rules.assertions.base import flatten_object, resolve_path
from astralint.codecs import load_file

__HERE__ = os.path.dirname(os.path.abspath(__file__))


def test_flatten_object():
    def get_member(flat_repr, path):
        for p, v in flat_repr:
            if p == path:
                return v
        raise KeyError(f"Path '{path}' not found in flattened object.")

    sample = load_file(os.path.join(__HERE__, "resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf"))
    flat = flatten_object(sample)
    assert get_member(flat, "variables") is not None
    assert get_member(flat, "attributes") is not None


def test_resolve_path():
    sample = load_file(os.path.join(__HERE__, "resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf"))
    assert resolve_path(sample, "attributes/.*") != []
    assert resolve_path(sample, "variables/.*") != []
    assert resolve_path(sample, "compression") == [("compression", "gzip_compression")]
    assert resolve_path(sample, "variables/.*/attributes/DEPEND_0") != []
