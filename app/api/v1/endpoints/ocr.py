import os
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.core.config import settings
from app.schemas.ocr import OcrTextResponse
from app.services.ocr_service import ocr_service
from app.services.image_preprocessor import ImagePreprocessingError

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post(
    "/extract-text",
    response_model=OcrTextResponse,
    summary="Extraer texto de una imagen vía OCR",
    description="Recibe una imagen (factura, recibo, ticket) y extrae las líneas de texto reconocidas.",
)
async def extract_text_from_image(
    file: UploadFile = File(..., description="Archivo de imagen (PNG, JPG, JPEG, WEBP)"),
) -> OcrTextResponse:
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        allowed = ", ".join(sorted(settings.ALLOWED_IMAGE_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato de archivo '{ext}' no soportado. Formatos permitidos: {allowed}",
        )

    # Leer contenido del archivo
    content = await file.read()
    max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El tamaño del archivo excede el límite permitido de {settings.MAX_IMAGE_SIZE_MB}MB.",
        )

    try:
        result = ocr_service.extract_from_image_bytes(content)
        return result
    except ImagePreprocessingError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante el procesamiento OCR: {str(err)}",
        ) from err
