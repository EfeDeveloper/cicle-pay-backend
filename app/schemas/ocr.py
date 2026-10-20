from typing import List, Optional
from pydantic import BaseModel, Field


class OcrTextResponse(BaseModel):
    """
    Respuesta estructurada para la extracción OCR inicial de documentos y facturas.
    """
    has_text: bool = Field(
        ...,
        description="Indica si se reconoció texto legible en el documento",
    )
    raw_text: str = Field(
        ...,
        description="Texto consolidado extraído por el lector OCR",
    )
    lines: List[str] = Field(
        default_factory=list,
        description="Lista de líneas reconocidas en el documento",
    )
    line_count: int = Field(
        ...,
        description="Número de líneas de texto identificadas",
    )
    message: Optional[str] = Field(
        default=None,
        description="Mensaje descriptivo (especialmente cuando has_text es False)",
    )
    processing_time_ms: float = Field(
        ...,
        description="Tiempo de procesamiento del OCR en milisegundos",
    )
