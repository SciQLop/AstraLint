class _Comp:
    def __init__(self, name: str):
        self.name = name


class _Item:
    """Stand-in for a pycdfpp CDF/Variable whose .compression may raise on an
    unknown CompressionType code (as a malformed/newer file produces)."""

    def __init__(self, comp):
        self._comp = comp

    @property
    def compression(self):
        if isinstance(self._comp, Exception):
            raise self._comp
        return self._comp


def test_compression_name_returns_known_name():
    from astralint.codecs.cdf import _compression_name

    assert _compression_name(_Item(_Comp("gzip"))) == "gzip"


def test_compression_name_handles_unknown_enum():
    from astralint.codecs.cdf import _compression_name

    bad = _Item(ValueError("312 is not a valid CompressionType"))
    assert _compression_name(bad) == "UNKNOWN"
