from enum import Enum

from pydantic import BaseModel


class DataType(str, Enum):
    NONE = "NONE"
    CHAR= "CHAR"
    UINT8 = "UINT8"
    UINT16 = "UINT16"
    UINT32 = "UINT32"
    UINT64 = "UINT64"
    INT8 = "INT8"
    INT16 = "INT16"
    INT32 = "INT32"
    INT64 = "INT64"
    FLOAT32 = "FLOAT32"
    FLOAT64 = "FLOAT64"
    TT2000 = "TT2000"
    CDFEPOCH = "CDFEPOCH"
    CDFEPOCH16 = "CDFEPOCH16"


class Attribute(BaseModel):
    name: str
    data_type: DataType

class VariableBits(BaseModel):
    compression:str
    data_type: DataType
    record_variance: bool

class Variable(BaseModel):
    name: str
    shape: list[int]
    attributes: dict[str, Attribute]
    config: VariableBits


class File(BaseModel):
    compression: str
    attributes: dict[str, Attribute]
    variables: dict[str, Variable]
