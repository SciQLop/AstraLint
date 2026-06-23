"""PDS4 structural auto-fix: re-save a CDF uncompressed and contiguous (CDF-A)."""

from pathlib import Path

import pycdfpp

from astralint.base.conformance_suite import ConformanceSuite, get_suite
from astralint.resolver import converge, resolve
from astralint.resolver.engine import _iter_failures
from astralint.resolver.loop import _load

RESOURCES = Path(__file__).parent / "resources"
MMS = RESOURCES / "mms1_asp2_srvy_l1b_stat_00000000_v01.cdf"  # gzip-compressed at file level


def pds4() -> ConformanceSuite:
    s = get_suite("PDS4")
    assert s is not None
    return s


def _mms_bytes() -> bytes:
    return MMS.read_bytes()


def test_resolve_emits_normalize_fix_for_compressed_cdf():
    file = _load(_mms_bytes(), MMS.name)
    results = pds4().run(file)
    fixes = resolve(file, results.failures_only())
    normalize = [f for f in fixes if f.action == "normalize"]
    assert normalize, "a compressed CDF must yield a structural normalize fix"
    assert normalize[0].auto, "decompression is lossless -> auto"
    assert normalize[0].disposition == "auto"


def test_converge_pds4_produces_uncompressed_contiguous_cdf():
    report, fixed = converge(_mms_bytes(), pds4(), filename=MMS.name)

    cdf = pycdfpp.load(fixed)
    assert cdf.compression == pycdfpp.CompressionType.no_compression
    assert all(v.compression == pycdfpp.CompressionType.no_compression for _, v in cdf.items())
    assert all(v.is_contiguous() for _, v in cdf.items())

    assert any(f.action == "normalize" for f in report.applied)
    # the file-compression error must be gone after the fix
    final = pds4().run(_load(fixed, MMS.name))
    remaining = {ref for ref, _ in _iter_failures(final)}
    assert "PDS4-CDFA-001" not in remaining


def test_no_normalize_fix_when_not_compressed():
    """A file with no compression/fragmentation failures gets no structural fix."""
    _, fixed = converge(_mms_bytes(), pds4(), filename=MMS.name)
    file = _load(fixed, MMS.name)
    results = pds4().run(file)
    fixes = resolve(file, results.failures_only())
    assert not [f for f in fixes if f.action == "normalize"]
