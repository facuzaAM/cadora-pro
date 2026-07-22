import logging
import os
import tempfile
import uuid as _uuid
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from app.cad.generator import CadGenerator
from app.cad.schemas import CadGenerateRequest, CadGenerateResponse
from app.config import settings
from app.database import get_db
from app.detection.schemas import (
    DoorDetectionResult,
    LineDetectionResult,
    WindowDetectionResult,
)
from app.detection.service import DetectionService
from app.ocr.schemas import OcrResult
from app.ocr.service import OcrService
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.services.plan_enforcer import enforce_conversion_limit
from app.services.storage_service import StorageService
from app.utils.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
detection_service = DetectionService()
ocr_service = OcrService()
storage = StorageService()


async def _download_doc_to_temp(
    user_id: UUID, project_id: UUID, doc, prefix: str = "cad"
) -> str:
    """Download a document to a safe temp file and return its path."""
    safe_name = os.path.basename(doc.filename).replace("/", "").replace("\\", "")
    tag = _uuid.uuid4().hex[:8]
    fd, path = tempfile.mkstemp(
        suffix=f"_{safe_name}", prefix=f"{user_id}_{project_id}_{prefix}_{tag}_"
    )
    os.close(fd)
    try:
        download_url = await storage.get_download_url(
            settings.STORAGE_BUCKET, doc.storage_path,
        )
        response = httpx.get(download_url)
        with open(path, "wb") as f:
            f.write(response.content)
    except Exception:
        if os.path.exists(path):
            os.remove(path)
        raise
    return path


def _merge_line_results(results: list[LineDetectionResult]) -> LineDetectionResult:
    merged = LineDetectionResult(
        lines=[], horizontal=[], vertical=[], diagonal=[],
        grouped_lines=[], intersections=[],
    )
    for r in results:
        merged.lines.extend(r.lines)
        merged.horizontal.extend(r.horizontal)
        merged.vertical.extend(r.vertical)
        merged.diagonal.extend(r.diagonal)
        merged.grouped_lines.extend(r.grouped_lines)
        merged.intersections.extend(r.intersections)
        if r.image_width > merged.image_width:
            merged.image_width = r.image_width
        if r.image_height > merged.image_height:
            merged.image_height = r.image_height
    return merged


def _merge_door_results(results: list[DoorDetectionResult]) -> DoorDetectionResult:
    merged = DoorDetectionResult(doors=[], image_width=0, image_height=0)
    for r in results:
        merged.doors.extend(r.doors)
        if r.image_width > merged.image_width:
            merged.image_width = r.image_width
        if r.image_height > merged.image_height:
            merged.image_height = r.image_height
    return merged


def _merge_window_results(results: list[WindowDetectionResult]) -> WindowDetectionResult:
    merged = WindowDetectionResult(windows=[], image_width=0, image_height=0)
    for r in results:
        merged.windows.extend(r.windows)
        if r.image_width > merged.image_width:
            merged.image_width = r.image_width
        if r.image_height > merged.image_height:
            merged.image_height = r.image_height
    return merged


def _merge_ocr_results(results: list[OcrResult]) -> OcrResult:
    merged = OcrResult(
        texts=[], measurements=[], room_names=[], scales=[], notes=[],
        raw_text="", page_count=0,
    )
    for r in results:
        merged.texts.extend(r.texts)
        merged.measurements.extend(r.measurements)
        merged.room_names.extend(r.room_names)
        merged.scales.extend(r.scales)
        merged.notes.extend(r.notes)
        if merged.raw_text and r.raw_text:
            merged.raw_text += "\n" + r.raw_text
        elif r.raw_text:
            merged.raw_text = r.raw_text
        merged.page_count += r.page_count
    return merged


async def _run_pipeline_on_docs(
    temp_paths: list[str],
) -> tuple[LineDetectionResult, DoorDetectionResult, WindowDetectionResult, OcrResult]:
    line_results = []
    door_results = []
    window_results = []
    ocr_results = []

    for path in temp_paths:
        line_results.append(await detection_service.process_file(path))
        door_results.append(await detection_service.process_file_doors(path))
        window_results.append(await detection_service.process_file_windows(path))
        ocr_results.append(await ocr_service.process_file(path))

    return (
        _merge_line_results(line_results),
        _merge_door_results(door_results),
        _merge_window_results(window_results),
        _merge_ocr_results(ocr_results),
    )


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
    docs = await doc_repo.list_by_project(project_id)
    if not docs:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="El proyecto no tiene documentos. Suba un plano primero.",
        )

    temp_paths = []
    output_path = ""
    try:
        for doc in docs:
            path = await _download_doc_to_temp(user.id, project_id, doc)
            temp_paths.append(path)

        lines_result, doors_result, windows_result, ocr_result = (
            await _run_pipeline_on_docs(temp_paths)
        )

        tag = _uuid.uuid4().hex[:8]
        fd, output_path = tempfile.mkstemp(
            suffix=".dxf", prefix=f"{user.id}_{project_id}_cadora_{tag}_"
        )
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
        logger.exception("Error generando CAD para proyecto %s", project_id)
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        for p in temp_paths:
            if p and os.path.exists(p):
                os.remove(p)
        if output_path and os.path.exists(output_path):
            os.remove(output_path)


@router.get("/download/{project_id}")
async def download_cad(
    project_id: UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the generated DXF for a project."""
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")

    doc_repo = DocumentRepository(db)
    docs = await doc_repo.list_by_project(project_id)
    if not docs:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="El proyecto no tiene documentos.",
        )

    temp_paths = []
    output_path = ""
    try:
        for doc in docs:
            path = await _download_doc_to_temp(user.id, project_id, doc, prefix="dl")
            temp_paths.append(path)

        lines_result, doors_result, windows_result, ocr_result = (
            await _run_pipeline_on_docs(temp_paths)
        )

        tag = _uuid.uuid4().hex[:8]
        fd, output_path = tempfile.mkstemp(
            suffix=".dxf", prefix=f"{user.id}_{project_id}_dl_{tag}_"
        )
        os.close(fd)

        generator = CadGenerator()
        generator.generate(
            lines_result=lines_result,
            doors_result=doors_result,
            windows_result=windows_result,
            ocr_result=ocr_result,
            output_path=output_path,
        )

        return FileResponse(
            path=output_path,
            filename=f"cadora_{project_id}.dxf",
            media_type="application/dxf",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error descargando CAD para proyecto %s", project_id)
        if output_path and os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        for p in temp_paths:
            if p and os.path.exists(p):
                os.remove(p)
