from functools import singledispatch

from pycdfpp import Attribute as CDFAttribute
from pycdfpp import DataType as CDFDataType
from pycdfpp import Variable as CDFVariable
from pycdfpp import VariableAttribute as CDFVariableAttribute
from pycdfpp import load

from ..base import (
    Attribute,
    Codec,
    DataType,
    File,
    Variable,
    classproperty,
    get_remote_file,
    is_remote_file,
)

type_mapping = {CDFDataType.CDF_CHAR: DataType.CHAR, CDFDataType.CDF_UCHAR: DataType.CHAR,
                CDFDataType.CDF_UINT1: DataType.UINT8, CDFDataType.CDF_UINT2: DataType.UINT16,
                CDFDataType.CDF_UINT4: DataType.UINT32, CDFDataType.CDF_INT1: DataType.INT8,
                CDFDataType.CDF_INT2: DataType.INT16, CDFDataType.CDF_INT4: DataType.INT32,
                CDFDataType.CDF_INT8: DataType.INT64, CDFDataType.CDF_FLOAT: DataType.FLOAT32,
                CDFDataType.CDF_REAL4: DataType.FLOAT32, CDFDataType.CDF_DOUBLE: DataType.FLOAT64,
                CDFDataType.CDF_REAL8: DataType.FLOAT64, CDFDataType.CDF_EPOCH: DataType.CDFEPOCH,
                CDFDataType.CDF_EPOCH16: DataType.CDFEPOCH16, CDFDataType.CDF_TIME_TT2000: DataType.TT2000,
                CDFDataType.CDF_NONE: DataType.NONE}


def _to_data_type(cdf_dtype: CDFDataType) -> DataType:
    return type_mapping.get(cdf_dtype)


@singledispatch
def _parse_attribute(attr) -> Attribute:
    raise NotImplementedError(f"Unsupported attribute type: {type(attr)}")


@_parse_attribute.register(CDFAttribute)
def _(attr: CDFAttribute) -> Attribute:
    if len(attr):
        data_type = [_to_data_type(attr.type(i)) for i in range(len(attr))]
    else:
        data_type = [DataType.NONE]
    return Attribute(name=attr.name, data_type=data_type, shape=[len(attr)])


@_parse_attribute.register(CDFVariableAttribute)
def _(attr: CDFVariableAttribute) -> Attribute:
    if len(attr):
        data_type = [_to_data_type(attr.type())]
    else:
        data_type = [DataType.NONE]
    return Attribute(name=attr.name, data_type=data_type, shape=[len(attr)])


def _parse_variable(var: CDFVariable) -> Variable:
    return Variable(
        name=var.name,
        shape=list(var.shape),
        attributes={name: _parse_attribute(attr) for name, attr in var.attributes.items()},
        compression=var.compression.name,
        record_variance=not var.is_nrv,
        data_type=_to_data_type(var.type)
    )


class CdfCodec(Codec):

    @classproperty
    def supported_extensions(cls) -> list[str]:
        return ["cdf"]

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
        if cdf := load(file):
            return File(
                extension="cdf",
                filename=fname,
                compression=cdf.compression.name,
                attributes={name: _parse_attribute(attr) for name, attr in cdf.attributes.items()},
                variables={name: _parse_variable(var) for name, var in cdf.items()}
            )
        else:
            raise ValueError(f"Could not load file {file} as CDF.")
