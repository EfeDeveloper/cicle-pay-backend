import io
from typing import Tuple
from PIL import Image, ImageOps, ImageEnhance, UnidentifiedImageError


class ImagePreprocessingError(Exception):
    """Excepción lanzada cuando la imagen no es válida o no puede ser procesada."""
    pass


from app.core.config import settings


def preprocess_image(
    image_bytes: bytes,
    max_dimension: int = None,
    enhance_contrast: bool = True,
) -> Tuple[Image.Image, Tuple[int, int]]:
    max_dimension = max_dimension or settings.IMAGE_MAX_DIMENSION
    """
    Carga y preprocesa los bytes de una imagen para optimizar la detección OCR.
    
    1. Valida que los bytes correspondan a una imagen válida.
    2. Corrige la orientación según los metadatos EXIF.
    3. Redimensiona proporcionalmente si excede max_dimension.
    4. Convierte a escala de grises y opcionalmente aumenta el contraste.
    
    Retorna:
        Tuple[Image.Image, Tuple[int, int]]: Imagen procesada y tamaño (ancho, alto).
    """
    if not image_bytes:
        raise ImagePreprocessingError("El archivo de imagen está vacío.")

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except (UnidentifiedImageError, Exception) as exc:
        raise ImagePreprocessingError(f"Formato de imagen inválido o corrupto: {str(exc)}") from exc

    # Corregir orientación por EXIF (típico en fotos de móviles)
    try:
        image = ImageOps.exif_transpose(image)
    except Exception:
        pass

    # Redimensionar si excede dimensiones máximas manteniendo relación de aspecto
    width, height = image.size
    if width > max_dimension or height > max_dimension:
        ratio = min(max_dimension / width, max_dimension / height)
        new_size = (int(width * ratio), int(height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    # Convertir a escala de grises para mejorar detección OCR
    processed = image.convert("L")

    # Aumento de contraste moderado para resaltar texto impreso
    if enhance_contrast:
        enhancer = ImageEnhance.Contrast(processed)
        processed = enhancer.enhance(1.4)

    return processed, processed.size
