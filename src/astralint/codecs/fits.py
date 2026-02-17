from astropy.io import fits

from ..base import (
    Attribute,
    Codec,
    DataType,
    File,
    Variable,
    get_remote_file,
    is_remote_file,
)

AnyHDU = fits.PrimaryHDU | fits.ImageHDU | fits.BinTableHDU | fits.TableHDU

HDUTypesNames = {
    fits.PrimaryHDU: "PrimaryHDU",
    fits.ImageHDU: "ImageHDU",
    fits.BinTableHDU: "BinTableHDU",
    fits.TableHDU: "TableHDU",
    fits.CompImageHDU: "CompImageHDU",
}

def _parse_headers(hdu:AnyHDU) -> dict[str, Attribute]:
    headers = {}
    for key, value in hdu.header.items():
        headers[key] = Attribute(
            name=key,
            data_type=[DataType.CHAR],
            shape=[1],
            values=[str(value)],
        )
    return headers

class FitsCodec(Codec):
    @classmethod
    def supported_extensions(cls) -> list[str]:
        return ["fits", "fit", "fts", "FITS", "FIT", "FTS"]

    @staticmethod
    def load(file_url_or_bytes: str | bytes) -> File | None:
        if isinstance(file_url_or_bytes, str) and is_remote_file(file_url_or_bytes):
            file = get_remote_file(file_url_or_bytes)
            fname = file_url_or_bytes.split("/")[-1]
        else:
            file = file_url_or_bytes
            if isinstance(file, str):
                fname = file.split("/")[-1]
            else:
                fname = "<bytes input>"
        if fits_file := fits.open(file):
            global_attributes : dict[str, Attribute]={}
            variables : dict[str, Variable]={}
            ext_hdu_count = {}
            for i, hdu in enumerate(fits_file):
                if isinstance(hdu, fits.PrimaryHDU):
                    global_attributes = _parse_headers(hdu)
                    name = HDUTypesNames.get(type(hdu))
                    variables[name] = Variable(
                        name=name,
                        data_type=DataType.UINT8,
                        shape=list(hdu.data.shape) if hdu.data is not None else [0],
                        attributes=global_attributes.copy(),
                        compression="none",
                        record_variance=False,
                    )
                else:
                    hdu_type_name = HDUTypesNames.get(type(hdu), str(type(hdu)))
                    name = f"{hdu_type_name}_{ext_hdu_count.get(type(hdu),0)}"
                    variables[name] = Variable(
                        name=name,
                        data_type=DataType.UINT8,
                        shape=list(hdu.data.shape) if hdu.data is not None else [0],
                        attributes=_parse_headers(hdu),
                        compression="none",
                        record_variance=False,
                    )
                    ext_hdu_count[type(hdu)] = ext_hdu_count.get(type(hdu), 0) + 1
            return File(
                extension="fits",
                filename=fname,
                compression="none",
                attributes=global_attributes,
                variables=variables,
            )
        else:
            raise ValueError(f"Could not load file {file} as FITS.")
