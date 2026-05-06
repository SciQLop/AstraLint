"""Tests for the FITS codec, focused on resource handling."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from astropy.io import fits

from astralint.codecs.fits import FitsCodec


@pytest.fixture
def fits_path(tmp_path: Path) -> Path:
    primary = fits.PrimaryHDU(data=np.zeros((4, 4), dtype=np.uint8))
    primary.header["TELESCOP"] = "TEST"
    image = fits.ImageHDU(data=np.zeros((2, 2), dtype=np.uint8), name="EXT1")
    hdul = fits.HDUList([primary, image])
    path = tmp_path / "test.fits"
    hdul.writeto(path)
    return path


class TestFitsCodecResourceHandling:
    def test_load_closes_underlying_hdulist(self, fits_path):
        real_open = fits.open
        captured: list = []

        def _spy(*args, **kwargs):
            hdul = real_open(*args, **kwargs)
            captured.append(hdul)
            return hdul

        with patch("astralint.codecs.fits.fits.open", side_effect=_spy):
            FitsCodec.load(str(fits_path))

        assert captured, "fits.open should have been called"
        # After load(), the HDUList must be closed (no associated file handle).
        for hdul in captured:
            assert hdul.fileinfo(0) is None or hdul._file is None or hdul._file.closed

    def test_load_returns_expected_structure(self, fits_path):
        result = FitsCodec.load(str(fits_path))
        assert result is not None
        assert result.filename == "test.fits"
        assert "TELESCOP" in result.attributes
        # Primary + one extension HDU
        assert len(result.variables) == 2

    def test_load_propagates_open_failure(self, tmp_path):
        bogus = tmp_path / "not_fits.fits"
        bogus.write_bytes(b"not a fits file")
        with pytest.raises(OSError):
            FitsCodec.load(str(bogus))


class TestFitsCodecBytesInput:
    def test_load_from_bytes(self, fits_path):
        data = fits_path.read_bytes()
        result = FitsCodec.load(data)
        assert result is not None
        assert result.filename == "<bytes input>"


class TestFitsCodecMockedOpen:
    def test_uses_context_manager(self, fits_path):
        # Build a real HDUList for valid contents, but verify __exit__ is called.
        real_hdul = fits.open(str(fits_path))
        wrapper = MagicMock(wraps=real_hdul)
        wrapper.__enter__ = MagicMock(return_value=real_hdul)
        wrapper.__exit__ = MagicMock(return_value=False)
        wrapper.__iter__ = lambda self: iter(real_hdul)

        with patch("astralint.codecs.fits.fits.open", return_value=wrapper):
            FitsCodec.load(str(fits_path))

        wrapper.__exit__.assert_called_once()
        real_hdul.close()
