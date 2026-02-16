from enum import Enum

from pydantic import BaseModel


class DataType(str, Enum): # noqa: UP042 # Simpler with pydantic, and we can still use it as a string for comparisons and error messages
    NONE = "NONE"
    CHAR = "CHAR"
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
    data_type: list[DataType]
    shape: list[int]


class Variable(BaseModel):
    name: str
    attributes: dict[str, Attribute]
    compression: str
    data_type: DataType
    record_variance: bool
    shape: list[int]


class File(BaseModel):
    extension: str
    filename: str
    compression: str
    attributes: dict[str, Attribute]
    variables: dict[str, Variable]
