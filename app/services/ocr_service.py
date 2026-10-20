import ssl
import time
import io
import warnings
from typing import List, Optional
import certifi
from PIL import Image
import torch
from app.core.config import settings
from app.schemas.ocr import OcrTextResponse
from app.services.image_preprocessor import preprocess_image

# Suprimir advertencias internas de tensores de PyTorch
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Configurar SSL context con certifi para verificación segura de certificados
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())


class OcrService:
    """
    Servicio de extracción óptica de caracteres (OCR) para facturas y recibos
    usando EasyOCR (100% Python/PyTorch, sin dependencias a nivel de sistema host).
    Optimizado para hardware de bajo consumo y SBC como Raspberry Pi 5.
    """

    def __init__(self):
        self._reader = None

    def _get_reader(self):
        if self._reader is None:
            # Limitar el número de hilos de PyTorch para no saturar todos los núcleos de la CPU
            if settings.OCR_NUM_THREADS > 0:
                torch.set_num_threads(settings.OCR_NUM_THREADS)
                try:
                    torch.set_num_interop_threads(1)
                except RuntimeError:
                    pass

            import easyocr
            # Inicializar con soporte para español e inglés en modo CPU sin logs ruidosos
            self._reader = easyocr.Reader(["es", "en"], gpu=False, verbose=False)
        return self._reader

    def _extract_text(self, processed_bytes: bytes) -> List[str]:
        """Extrae las líneas de texto utilizando EasyOCR."""
        reader = self._get_reader()
        return reader.readtext(processed_bytes, detail=0)

    def extract_from_image_bytes(self, image_bytes: bytes) -> OcrTextResponse:
        """
        Preprocesa los bytes de una imagen y extrae el texto legible vía OCR.
        """
        start_time = time.perf_counter()

        # 1. Preprocesar imagen
        processed_img, _ = preprocess_image(image_bytes)

        # 2. Convertir imagen a buffer PNG en memoria para el lector OCR
        img_buffer = io.BytesIO()
        processed_img.save(img_buffer, format="PNG")
        processed_bytes = img_buffer.getvalue()

        # 3. Extraer texto
        extracted_lines = self._extract_text(processed_bytes)

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
            )

        consolidated = "\n".join(lines)
        return OcrTextResponse(
            has_text=True,
            raw_text=consolidated,
            lines=lines,
            line_count=len(lines),
            message=None,
            processing_time_ms=elapsed_ms,
        )


ocr_service = OcrService()
