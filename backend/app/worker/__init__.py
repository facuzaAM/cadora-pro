"""Background worker for async detection processing."""

from loguru import logger

from app.cad import CadGenerator
from app.config import settings
from app.detection.service import DetectionService
from app.ocr.service import OcrService
from app.services.storage_service import StorageService


async def process_detection(document_id: str, project_id: str) -> dict:
    """Run the full detection pipeline for a document.

    Returns a dict with detection results and generated file paths.
    """
    logger.info("Starting detection pipeline for doc={} project={}", document_id, project_id)

    storage = StorageService()
    detection_service = DetectionService()
    ocr_service = OcrService()
    cad_generator = CadGenerator()

    temp_path = f"/tmp/{project_id}_{document_id}_detect"

    try:
        download_url = await storage.get_download_url(
            settings.STORAGE_BUCKET, document_id,
        )

        import httpx
        response = httpx.get(download_url)
        with open(temp_path, "wb") as f:
            f.write(response.content)

        logger.info("Running line detection for project={}", project_id)
        lines_result = await detection_service.process_file(temp_path)

        logger.info("Running door detection for project={}", project_id)
        doors_result = await detection_service.process_file_doors(temp_path)

        logger.info("Running window detection for project={}", project_id)
        windows_result = await detection_service.process_file_windows(temp_path)

        logger.info("Running OCR for project={}", project_id)
        ocr_result = await ocr_service.process_file(temp_path)

        output_path = f"/tmp/{project_id}_{document_id}_cadora.dxf"
        cad_generator.generate(
            lines_result=lines_result,
            doors_result=doors_result,
            windows_result=windows_result,
            ocr_result=ocr_result,
            output_path=output_path,
        )

        logger.info("Detection pipeline completed for project={}", project_id)

        return {
            "lines": lines_result,
            "doors": doors_result,
            "windows": windows_result,
            "ocr": ocr_result,
            "output_path": output_path,
        }
    except Exception as e:
        logger.error("Detection pipeline failed for project={}: {}", project_id, e)
        raise
    finally:
        import os
        for p in [temp_path]:
            if os.path.exists(p):
                os.remove(p)
