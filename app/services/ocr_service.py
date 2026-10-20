import io
import logging
import os
import shutil
import ssl
import time
import warnings
from typing import List, Optional, Tuple

import certifi
from PIL import Image
import pytesseract

from app.core.config import settings
from app.schemas.ocr import OcrTextResponse
from app.services.image_preprocessor import preprocess_image

logger = logging.getLogger(__name__)

# Suprimir advertencias internas de tensores de PyTorch
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Configurar SSL context con certifi para verificación segura de certificados
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())


class OcrService:
    """
    Servicio híbrido de extracción óptica de caracteres (OCR) para facturas y recibos.
    - Modo Alta Velocidad (Producción / Dokploy): Utiliza Tesseract C++ nativo instalado
      vía aptPkgs ('tesseract-ocr' y 'tesseract-ocr-spa') ejecutándose en ~0.3 - 0.8s.
    - Modo Portátil / Desarrollo Local: Si no hay binario tesseract en el sistema,
      utiliza EasyOCR de forma opcional con canvas optimizado y sin saturar CPU.
    """

    def __init__(self):
        self._reader = None
        self._tesseract_cmd = shutil.which("tesseract")

    @property
    def has_tesseract(self) -> bool:
        return self._tesseract_cmd is not None

    def _get_reader(self):
        """Inicializa EasyOCR de forma perezosa (lazy) solo si se necesita."""
        if self._reader is None:
            try:
                import torch
                if settings.OCR_NUM_THREADS > 0:
                    torch.set_num_threads(settings.OCR_NUM_THREADS)
                    try:
                        torch.set_num_interop_threads(1)
                    except RuntimeError:
                        pass
            except ImportError:
                pass

            try:
                import easyocr
                self._reader = easyocr.Reader(["es", "en"], gpu=False, verbose=False)
            except ImportError as err:
                raise RuntimeError(
                    "No se encontró el motor OCR nativo 'tesseract' ni la librería 'easyocr'. "
                    "En producción asegúrate de tener instalado 'tesseract-ocr' y 'tesseract-ocr-spa', "
                    "o instala 'easyocr' para desarrollo local."
                ) from err

        return self._reader

    def _extract_text(self, processed_img: Image.Image, processed_bytes: bytes) -> Tuple[List[str], str]:
        """
        Extrae texto usando Tesseract si está disponible en el entorno (Dokploy/Linux),
        o EasyOCR como fallback para desarrollo local.
        Retorna la lista de líneas y el nombre del motor utilizado.
        """
        use_tesseract = (
            settings.OCR_ENGINE == "tesseract"
            or (settings.OCR_ENGINE == "auto" and self.has_tesseract)
        )

        if use_tesseract:
            try:
                # Intentar con español + inglés si los traineddata están presentes,
                # o fallback al idioma por defecto de Tesseract
                try:
                    text = pytesseract.image_to_string(processed_img, lang="spa+eng")
                except Exception:
                    text = pytesseract.image_to_string(processed_img)

                lines = [line.strip() for line in text.splitlines() if line.strip()]
                if lines:
                    return lines, "tesseract"
            except Exception as err:
                logger.warning("Fallo al ejecutar Tesseract (%s). Intentando EasyOCR...", err)

        # Fallback a EasyOCR si está disponible
        reader = self._get_reader()
        lines = reader.readtext(
            processed_bytes,
            detail=0,
            canvas_size=settings.EASYOCR_CANVAS_SIZE,
            mag_ratio=1.0,
        )
        return lines, "easyocr"

    def extract_from_image_bytes(self, image_bytes: bytes) -> OcrTextResponse:
        """
        Preprocesa los bytes de una imagen y extrae el texto legible vía OCR.
        """
        start_time = time.perf_counter()

        # 1. Preprocesar imagen
        processed_img, _ = preprocess_image(image_bytes)

        # 2. Convertir imagen a buffer PNG en memoria
        img_buffer = io.BytesIO()
        processed_img.save(img_buffer, format="PNG")
        processed_bytes = img_buffer.getvalue()

        # 3. Extraer texto con motor híbrido
        extraction_result = self._extract_text(processed_img, processed_bytes)
        if isinstance(extraction_result, tuple):
            extracted_lines, engine_used = extraction_result
        else:
            extracted_lines, engine_used = extraction_result, "ocr"

        # 4. Limpiar líneas vacías

        lines = [line.strip() for line in extracted_lines if line.strip()]
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if not lines:
            return OcrTextResponse(
                has_text=False,
                raw_text="",
                lines=[],
                line_count=0,
                message="No se detectó texto legible en el documento",
                processing_time_ms=elapsed_ms,
                engine=engine_used,
            )

        consolidated = "\n".join(lines)
        return OcrTextResponse(
            has_text=True,
            raw_text=consolidated,
            lines=lines,
            line_count=len(lines),
            message=None,
            processing_time_ms=elapsed_ms,
            engine=engine_used,
        )


ocr_service = OcrService()

