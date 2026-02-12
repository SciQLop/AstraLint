from typing import Optional
from functools import singledispatch
from pycdfpp import load, Attribute as CDFAttribute, Variable as CDFVariable, VariableAttribute as CDFVariableAttribute, \
    DataType as CDFDataType
from ..base import Codec, File, Variable, Attribute, VariableBits, DataType,classproperty
from .codecs import register_codec

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
        data_type = _to_data_type(attr.type(0))
    else:
        data_type = DataType.NONE
    return Attribute(name=attr.name, data_type=data_type)

@_parse_attribute.register(CDFVariableAttribute)
def _(attr: CDFVariableAttribute) -> Attribute:
    if len(attr):
        data_type = _to_data_type(attr.type())
    else:
        data_type = DataType.NONE
    return Attribute(name=attr.name, data_type=data_type)


def _parse_variable(var: CDFVariable) -> Variable:
    return Variable(
        name=var.name,
        shape=list(var.shape),
        attributes={name: _parse_attribute(attr) for name, attr in var.attributes.items()},
        config=VariableBits(compression=var.compression.name, record_variance=not var.is_nrv,
                            data_type=_to_data_type(var.type))
    )


@register_codec
class CdfCodec(Codec):

    @classproperty
    def supported_extensions(cls) -> list[str]:
        return ["cdf"]

    @staticmethod
    def load(file: str) -> Optional[File]:
        if cdf := load(file):
            return File(
                compression=cdf.compression.name,
                attributes={name: _parse_attribute(attr) for name, attr in cdf.attributes.items()},
                variables={name: _parse_variable(var) for name, var in cdf.items()}
            )
        else:
            raise ValueError(f"Could not load file {file} as CDF.")
