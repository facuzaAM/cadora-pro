
from pydantic import BaseModel


class CadGenerateRequest(BaseModel):
    format: str = "dxf"


class CadGenerateResponse(BaseModel):
    filename: str
    file_size: int
