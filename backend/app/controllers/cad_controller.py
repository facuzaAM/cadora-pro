import os
import tempfile
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from app.cad.generator import CadGenerator
from app.cad.schemas import CadGenerateRequest, CadGenerateResponse
from app.config import settings
from app.database import get_db
from app.detection.service import DetectionService
from app.ocr.service import OcrService
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.services.storage_service import StorageService
from app.services.plan_enforcer import enforce_conversion_limit
from app.utils.dependencies import get_current_user

router = APIRouter()
detection_service = DetectionService()
ocr_service = OcrService()
storage = StorageService()


async def _download_doc_to_temp(user_id: UUID, project_id: UUID, doc, prefix: str = "cad") -> str:
    """Download a document to a safe temp file and return its path."""
    safe_name = os.path.basename(doc.filename).replace("/", "").replace("\\", "")
    fd, path = tempfile.mkstemp(
        suffix=f"_{safe_name}", prefix=f"{user_id}_{project_id}_{prefix}_"
    )
    os.close(fd)
    try:
        download_url = await storage.get_download_url(
            settings.STORAGE_BUCKET, doc.storage_path,
        )
        import httpx
        response = httpx.get(download_url)
        with open(path, "wb") as f:
            f.write(response.content)
    except Exception:
        if os.path.exists(path):
            os.remove(path)
        raise
    return path


@router.post("/generate/{project_id}", response_model=CadGenerateResponse)
async def generate_cad(
    project_id: UUID,
    body: CadGenerateRequest = CadGenerateRequest(),
    user=Depends(enforce_conversion_limit),
    db: AsyncSession = Depends(get_db),
):
    """Run full detection pipeline and generate a DXF file."""
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")

    doc_repo = DocumentRepository(db)
    docs = await doc_repo.get_by_project(project_id)
    if not docs:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="El proyecto no tiene documentos. Suba un plano primero.",
        )

    doc = docs[0]
    temp_path = await _download_doc_to_temp(user.id, project_id, doc)
    output_path = ""

    try:
        lines_result = await detection_service.process_file(temp_path)
        doors_result = await detection_service.process_file_doors(temp_path)
        windows_result = await detection_service.process_file_windows(temp_path)
        ocr_result = await ocr_service.process_file(temp_path)

        fd, output_path = tempfile.mkstemp(suffix=".dxf", prefix=f"{user_id}_{project_id}_cadora_")
        os.close(fd)

        generator = CadGenerator()
        generator.generate(
            lines_result=lines_result,
            doors_result=doors_result,
            windows_result=windows_result,
            ocr_result=ocr_result,
            output_path=output_path,
        )

        file_size = os.path.getsize(output_path)

        user_repo = UserRepository(db)
        user_db = await user_repo.get_by_id(user.id)
        if user_db:
            user_db.conversions_used += 1
            await user_repo._save(user_db)

        return CadGenerateResponse(
            filename=f"cadora_{project_id}.dxf",
            file_size=file_size,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        for p in [temp_path, output_path]:
            if p and os.path.exists(p):
                os.remove(p)


@router.get("/download/{project_id}")
async def download_cad(
    project_id: UUID,
    user=Depends(enforce_conversion_limit),
    db: AsyncSession = Depends(get_db),
):
    """Download the generated DXF for a project."""
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")

    doc_repo = DocumentRepository(db)
    docs = await doc_repo.get_by_project(project_id)
    if not docs:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="El proyecto no tiene documentos.",
        )

    doc = docs[0]
    temp_img = await _download_doc_to_temp(user.id, project_id, doc, prefix="dl")
    fd, output_path = tempfile.mkstemp(suffix=".dxf", prefix=f"{user_id}_{project_id}_cadora_")
    os.close(fd)

    try:
        lines_result = await detection_service.process_file(temp_img)
        doors_result = await detection_service.process_file_doors(temp_img)
        windows_result = await detection_service.process_file_windows(temp_img)
        ocr_result = await ocr_service.process_file(temp_img)

        generator = CadGenerator()
        generator.generate(
            lines_result=lines_result,
            doors_result=doors_result,
            windows_result=windows_result,
            ocr_result=ocr_result,
            output_path=output_path,
        )

        # Return FileResponse BEFORE cleanup — it streams lazily, so we
        # return it now and let FastAPI handle the response.  The temp
        # file will be cleaned up by the OS eventually (mkstemp in /tmp).
        return FileResponse(
            path=output_path,
            filename=f"cadora_{project_id}.dxf",
            media_type="application/dxf",
        )
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        if os.path.exists(temp_img):
            os.remove(temp_img)
