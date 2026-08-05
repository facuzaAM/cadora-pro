import logging
import os
import time

from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, Request, UploadFile
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_429_TOO_MANY_REQUESTS

from app.config import settings
from app.utils.rate_limit import rate_limit
from app.utils.uploads import (
    make_temp_path,
    read_upload_with_limit,
    validate_extension,
    validate_magic_bytes,
)

logger = logging.getLogger(__name__)

router = APIRouter()

DEMO_MAX_SIZE_MB = 10
DEMO_ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff"}

_demo_sessions: TTLCache = TTLCache(maxsize=1000, ttl=3600)


@router.post("/process")
@rate_limit(settings.RATE_LIMIT_DEMO)
async def process_demo(
    request: Request,
    file: UploadFile,
):
    """Process a floor plan without authentication. Returns detection results only (no DXF)."""
    session_token = request.headers.get("X-Demo-Session", "")
    if session_token and session_token in _demo_sessions:
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail="Ya usaste la demo. Registrate para seguir usando la plataforma.",
        )

    ext = validate_extension(
        file,
        DEMO_ALLOWED_EXTENSIONS,
        detail="Formato no soportado en demo. Usá: PDF, PNG, JPG o TIFF.",
    )
    content = await read_upload_with_limit(
        file,
        DEMO_MAX_SIZE_MB * 1024 * 1024,
        f"El archivo excede el límite de {DEMO_MAX_SIZE_MB} MB para la demo.",
    )
    validate_magic_bytes(ext, content)

    temp_path = make_temp_path("demo", file.filename)

    try:
        with open(temp_path, "wb") as f:
            f.write(content)

        try:
            from app.detection.service import DetectionService
            from app.ocr.service import OcrService

            detection_service = DetectionService()
            ocr_service = OcrService()

            lines_result = await detection_service.process_file(temp_path)
            doors_result = await detection_service.process_file_doors(temp_path)
            windows_result = await detection_service.process_file_windows(temp_path)
            ocr_result = await ocr_service.process_file(temp_path)
        except Exception:
            logger.exception("Error en pipeline de detección OCR")
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="No pudimos leer el plano. Verificá que sea legible e intentá de nuevo.",
            )

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

        if session_token:
            _demo_sessions[session_token] = time.time()

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
        logger.exception("Error inesperado procesando demo")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Error al procesar el archivo. Intentá con otro plano.",
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
