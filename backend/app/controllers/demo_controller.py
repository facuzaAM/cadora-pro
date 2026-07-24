import logging
import os
import tempfile
import uuid as _uuid

from fastapi import APIRouter, HTTPException, Request, UploadFile
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_413_CONTENT_TOO_LARGE

from app.detection.service import DetectionService
from app.ocr.service import OcrService
from app.utils.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()
detection_service = DetectionService()
ocr_service = OcrService()

DEMO_MAX_SIZE_MB = 10
DEMO_ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff"}


def _validate_demo_file(file: UploadFile) -> str:
    if not file.filename:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Archivo no proporcionado")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if f".{ext}" not in DEMO_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Formato .{ext} no soportado en demo. Usa: PDF, PNG, JPG o TIFF.",
        )
    return ext


async def _read_with_limit(file: UploadFile) -> bytes:
    max_bytes = DEMO_MAX_SIZE_MB * 1024 * 1024
    content = b""
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        content += chunk
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=HTTP_413_CONTENT_TOO_LARGE,
                detail=f"El archivo excede el límite de {DEMO_MAX_SIZE_MB} MB para la demo.",
            )
    return content


@router.post("/process")
@limiter.limit("1/60seconds")
async def process_demo(
    request: Request,
    file: UploadFile,
):
    """Process a floor plan without authentication. Returns detection results only (no DXF)."""
    _validate_demo_file(file)
    content = await _read_with_limit(file)

    tag = _uuid.uuid4().hex[:8]
    fd, temp_path = tempfile.mkstemp(
        suffix=f"_{file.filename}", prefix=f"demo_{tag}_"
    )
    os.close(fd)

    try:
        with open(temp_path, "wb") as f:
            f.write(content)

        lines_result = await detection_service.process_file(temp_path)
        doors_result = await detection_service.process_file_doors(temp_path)
        windows_result = await detection_service.process_file_windows(temp_path)
        ocr_result = await ocr_service.process_file(temp_path)

        image_width = (
            lines_result.image_width
            or doors_result.image_width
            or windows_result.image_width
        )
        image_height = (
            lines_result.image_height
            or doors_result.image_height
            or windows_result.image_height
        )

        return {
            "walls": [wall.model_dump(mode="json") for wall in lines_result.lines],
            "doors": [door.model_dump(mode="json") for door in doors_result.doors],
            "windows": [win.model_dump(mode="json") for win in windows_result.windows],
            "ocr_texts": [txt.model_dump(mode="json") for txt in ocr_result.texts],
            "ocr_measurements": [m.model_dump(mode="json") for m in ocr_result.measurements],
            "image_width": image_width,
            "image_height": image_height,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error procesando demo")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Error al procesar el archivo. Intentá con otro plano.",
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
