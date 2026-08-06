
from pydantic import BaseModel, field_validator

from app.editor.schemas import ElementsPayload


class CadGenerateRequest(BaseModel):
    format: str = "dxf"
    force: bool = False
    elements: ElementsPayload | None = None

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v.lower() not in ("dxf", "dwg"):
            raise ValueError("Formato inválido. Use 'dxf' o 'dwg'.")
        return v.lower()


class CadGenerateResponse(BaseModel):
    filename: str
    file_size: int
