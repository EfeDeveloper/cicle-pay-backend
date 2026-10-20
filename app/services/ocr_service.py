import ssl
import time
import io
import shutil
import warnings
from typing import List, Optional
import certifi
from PIL import Image
import torch
import pytesseract
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
    Servicio híbrido de extracción óptica de caracteres (OCR) para facturas y recibos.
    - Modo Alta Velocidad (Nixpacks / Dokploy en Raspberry Pi): Si detecta el binario 'tesseract'
      instalado en el contenedor, lo ejecuta vía C++ en ~0.5 - 1s.
    - Modo Portátil / Desarrollo Local: Si no hay binario en el host, utiliza EasyOCR
      con canvas optimizado y multi-hilo acotado para evitar saturación de CPU.
    """

    def __init__(self):
        self._reader = None
        self._tesseract_cmd = shutil.which("tesseract")

    @property
    def has_tesseract(self) -> bool:
        return self._tesseract_cmd is not None

    def _get_reader(self):
        if self._reader is None:
            # Limitar hilos de PyTorch según configuración
            if settings.OCR_NUM_THREADS > 0:
                torch.set_num_threads(settings.OCR_NUM_THREADS)
                try:
                    torch.set_num_interop_threads(1)
                except RuntimeError:
                    pass

            import easyocr
            # Inicializar con soporte para español e inglés
            self._reader = easyocr.Reader(["es", "en"], gpu=False, verbose=False)
        return self._reader

    def _extract_text(self, processed_img: Image.Image, processed_bytes: bytes) -> List[str]:
        """
        Extrae texto usando Tesseract si está disponible en el entorno (Dokploy/Linux),
        o EasyOCR con canvas optimizado en desarrollo local.
        """
        use_tesseract = (
            settings.OCR_ENGINE == "tesseract"
            or (settings.OCR_ENGINE == "auto" and self.has_tesseract)
        )

        if use_tesseract:
            try:
                # Tesseract C++ nativo: ultra rápido (< 1s en Raspberry Pi 5)
                text = pytesseract.image_to_string(processed_img)
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                if lines:
                    return lines
            except Exception:
                pass  # Fallback a EasyOCR si Tesseract falla

        # Fallback a EasyOCR optimizado con canvas controlado
        reader = self._get_reader()
        return reader.readtext(
            processed_bytes,
            detail=0,
            canvas_size=settings.EASYOCR_CANVAS_SIZE,
            mag_ratio=1.0,
        )

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
        extracted_lines = self._extract_text(processed_img, processed_bytes)

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
