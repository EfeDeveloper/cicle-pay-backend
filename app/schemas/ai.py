import re
import unicodedata
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


# Las 10 categorías estrictas de CyclePay
CYCLEPAY_CATEGORIES = (
    "Vivienda",
    "Servicios",
    "Alimentación",
    "Transporte",
    "Salud",
    "Educación",
    "Entretenimiento",
    "Seguros",
    "Suscripciones",
    "Otros",
)

ExpenseCategory = Literal[
    "Vivienda",
    "Servicios",
    "Alimentación",
    "Transporte",
    "Salud",
    "Educación",
    "Entretenimiento",
    "Seguros",
    "Suscripciones",
    "Otros",
]


def normalize_category_name(raw_cat: str) -> str:
    """
    Normaliza texto de categoría (eliminando tildes y comparando en minúsculas)
    para mapear a las 10 categorías oficiales de CyclePay.
    """
    def strip_accents(text: str) -> str:
        return "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        ).lower().strip()

    cleaned = strip_accents(raw_cat)
    lookup = {strip_accents(cat): cat for cat in CYCLEPAY_CATEGORIES}

    # Coincidencia directa normalizada
    if cleaned in lookup:
        return lookup[cleaned]

    # Coincidencias aproximadas por palabras clave comunes
    keywords = {
        "comida": "Alimentación",
        "mercado": "Alimentación",
        "supermercado": "Alimentación",
        "restaurante": "Alimentación",
        "gasolina": "Transporte",
        "uber": "Transporte",
        "taxi": "Transporte",
        "peaje": "Transporte",
        "luz": "Servicios",
        "agua": "Servicios",
        "gas": "Servicios",
        "internet": "Servicios",
        "telefono": "Servicios",
        "arriendo": "Vivienda",
        "alquiler": "Vivienda",
        "medico": "Salud",
        "farmacia": "Salud",
        "droga": "Salud",
        "colegio": "Educación",
        "universidad": "Educación",
        "curso": "Educación",
        "cine": "Entretenimiento",
        "poliza": "Seguros",
        "seguro": "Seguros",
        "netflix": "Suscripciones",
        "spotify": "Suscripciones",
    }
    for kw, target in keywords.items():
        if kw in cleaned:
            return target

    return "Otros"


class OcrExpenseExtractRequest(BaseModel):
    """
    Petición para extraer información estructurada de gasto desde texto OCR.
    """
    raw_text: str = Field(
        ...,
        min_length=1,
        description="Texto plano consolidado extraído por el motor OCR",
    )
    period_key: Optional[str] = Field(
        default=None,
        description="Período sugerido en formato YYYY-MM. Si es nulo, se infiere del documento o mes corriente.",
    )


class AdditionalExpensePayload(BaseModel):
    """
    Contrato estricto de gasto adicional compatible con CreateManualExpenseInput / MonthlyExpense de CyclePay.
    """
    name: str = Field(
        ...,
        min_length=1,
        description="Nombre del comercio, emisor o concepto del gasto",
    )
    amount: float = Field(
        ...,
        gt=0,
        description="Monto total del gasto (debe ser mayor a 0)",
    )
    category: ExpenseCategory = Field(
        ...,
        description="Categoría estricta de CyclePay",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=140,
        description="Detalle o descripción concisa del gasto (máximo 140 caracteres)",
    )
    dueDay: Optional[int] = Field(
        default=None,
        ge=1,
        le=31,
        description="Día del mes (1–31) en que se emitió o vence el gasto, o null",
    )
    periodKey: str = Field(
        ...,
        description="Período de imputación en formato YYYY-MM",
    )
    status: Literal["pending", "paid"] = Field(
        default="pending",
        description="Estado del gasto: 'paid' si el recibo evidencia pago, 'pending' si es factura por pagar",
    )
    source: Literal["manual"] = Field(
        default="manual",
        description="Origen del gasto adicional (siempre 'manual')",
    )
    templateId: Optional[Literal[None]] = Field(
        default=None,
        description="Siempre null para gastos adicionales no recurrentes",
    )

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("El nombre del gasto no puede estar vacío.")
        return trimmed

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if not isinstance(v, str):
            return "Otros"
        return normalize_category_name(v)

    @field_validator("periodKey")
    @classmethod
    def validate_period_key(cls, v: str) -> str:
        pattern = r"^\d{4}-(0[1-9]|1[0-2])$"
        if not re.match(pattern, v):
            # Si viene mal formateado, fallback al mes actual
            now = datetime.now()
            return f"{now.year:04d}-{now.month:02d}"
        return v

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        trimmed = v.strip()
        return trimmed[:140] if trimmed else None

    @field_validator("dueDay", mode="before")
    @classmethod
    def clean_due_day(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        try:
            val = int(v)
            if 1 <= val <= 31:
                return val
        except (ValueError, TypeError):
            pass
        return None


class AiExpenseExtractResponse(BaseModel):
    """
    Respuesta estructurada del servicio de IA de extracción de gasto.
    """
    success: bool = Field(
        ...,
        description="Indica si la extracción fue exitosa",
    )
    expense: Optional[AdditionalExpensePayload] = Field(
        default=None,
        description="Carga útil del gasto adicional lista para crear en CyclePay",
    )
    processing_time_ms: float = Field(
        ...,
        description="Tiempo total empleado en la inferencia y procesamiento en milisegundos",
    )
    model: Optional[str] = Field(
        default=None,
        description="Nombre del modelo de IA utilizado para la inferencia",
    )
    message: Optional[str] = Field(
        default=None,
        description="Mensaje informativo o de error descriptivo",
    )
