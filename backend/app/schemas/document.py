from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: UUID
    project_id: UUID
    filename: str
    file_type: str
    file_size: int
    storage_path: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    id: UUID
    filename: str
    file_type: str
    file_size: int
    download_url: str
    created_at: datetime
