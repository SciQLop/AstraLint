from astralint.base.file import File
from astralint.resolver.sources.filename import (
    data_version_from_filename,
    logical_file_id_from_filename,
    logical_source_from_filename,
)


def _file(filename: str) -> File:
    return File(extension="cdf", filename=filename, compression="NONE", attributes={}, variables={})


def test_logical_file_id_is_the_stem():
    f = _file("solo_l2_rpw-lfr-surv-swf-b_20220221_v02.cdf")
    out = logical_file_id_from_filename(f, None, "Logical_file_id", None)
    assert out is not None
    assert out.value == "solo_l2_rpw-lfr-surv-swf-b_20220221_v02"


def test_logical_source_drops_date_and_version():
    f = _file("solo_l2_rpw-lfr-surv-swf-b_20220221_v02.cdf")
    out = logical_source_from_filename(f, None, "Logical_source", None)
    assert out is not None
    assert out.value == "solo_l2_rpw-lfr-surv-swf-b"


def test_data_version_from_vNN():
    f = _file("solo_l2_rpw-lfr-surv-swf-b_20220221_v02.cdf")
    out = data_version_from_filename(f, None, "Data_version", None)
    assert out is not None
    assert out.value == "02"


def test_multi_token_source_matches():
    f = _file("mms1_asp2_srvy_l1b_stat_00000000_v01.cdf")
    src = logical_source_from_filename(f, None, "Logical_source", None)
    fid = logical_file_id_from_filename(f, None, "Logical_file_id", None)
    assert src is not None and src.value == "mms1_asp2_srvy_l1b_stat"
    assert fid is not None and fid.value == "mms1_asp2_srvy_l1b_stat_00000000_v01"


def test_non_conventional_filename_returns_none():
    f = _file("random_file.cdf")
    assert logical_file_id_from_filename(f, None, "Logical_file_id", None) is None
    assert logical_source_from_filename(f, None, "Logical_source", None) is None
    assert data_version_from_filename(f, None, "Data_version", None) is None


def test_no_version_token_still_derives_id_and_source():
    f = _file("solo_l2_rpw_20220221.cdf")  # no _vNN
    assert data_version_from_filename(f, None, "Data_version", None) is None
    fid = logical_file_id_from_filename(f, None, "Logical_file_id", None)
    src = logical_source_from_filename(f, None, "Logical_source", None)
    assert fid is not None and fid.value == "solo_l2_rpw_20220221"
    assert src is not None and src.value == "solo_l2_rpw"
