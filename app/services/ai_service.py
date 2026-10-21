import json
import re
import time
from datetime import datetime
from typing import Any, Dict, Optional
import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.ai import (
    AdditionalExpensePayload,
    AiExpenseExtractResponse,
    OcrExpenseExtractRequest,
)


class AiServiceError(Exception):
    """Excepción base para errores del servicio de IA."""
    pass


class AiConnectionError(AiServiceError):
    """Excepción cuando no es posible conectar con Ollama."""
    pass


class AiTimeoutError(AiServiceError):
    """Excepción cuando la llamada a Ollama excede el tiempo límite."""
    pass


class AiUnprocessableExpenseError(AiServiceError):
    """Excepción cuando el texto OCR no contiene datos suficientes para estructurar un gasto."""
    pass


class AiExpenseService:
    """
    Servicio encargado de enviar texto OCR a Ollama para extraer
    y validar un gasto adicional para CyclePay.
    """

    SYSTEM_PROMPT = (
        "Eres un asistente experto en contabilidad y análisis financiero para CyclePay.\n"
        "Tu objetivo es analizar el texto de facturas o comprobantes extraído por OCR y estructurarlo "
        "EXCLUSIVAMENTE como un gasto adicional puntual (no recurrente ni plantilla).\n\n"
        "Debes responder ÚNICAMENTE con un objeto JSON válido con las siguientes claves:\n"
        '- "name": (string, obligatorio) Nombre del comercio, proveedor o concepto principal.\n'
        '- "amount": (number, obligatorio) Monto total pagado o por pagar como número positivo (ej: 45000.0).\n'
        '- "category": (string, obligatorio) Debe ser EXACTAMENTE una de: '
        '["Vivienda", "Servicios", "Alimentación", "Transporte", "Salud", "Educación", "Entretenimiento", "Seguros", "Suscripciones", "Otros"].\n'
        '- "description": (string o null) Breve detalle del gasto (máximo 140 caracteres).\n'
        '- "dueDay": (integer 1-31 o null) Día del mes del documento o vencimiento.\n'
        '- "periodKey": (string "YYYY-MM") Período año-mes del gasto.\n'
        '- "status": ("pending" o "paid") "paid" si es recibo/ticket pagado, "pending" si es cuenta por pagar.\n\n'
        "Reglas:\n"
        "1. No incluyas texto antes o después del JSON.\n"
        '2. Si el texto no contiene datos de gasto o monto identificable, responde: {"error": "unextractable_expense"}\n'
    )

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds or settings.OLLAMA_TIMEOUT_SECONDS

    @staticmethod
    def _sanitize_json_response(raw_text: str) -> Dict[str, Any]:
        """
        Extrae y decodifica un diccionario JSON de la respuesta de texto del modelo,
        removiendo bloques de markdown ```json ... ``` si estuvieran presentes.
        """
        text = raw_text.strip()

        # Remover bloques de código markdown
        if "```" in text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                text = match.group(1).strip()

        # Si aún hay texto circundante, buscar el bloque JSON exterior
        if not (text.startswith("{") and text.endswith("}")):
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                text = match.group(0).strip()

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            raise ValueError("El resultado JSON no es un objeto de primer nivel.")
        except json.JSONDecodeError as err:
            raise AiUnprocessableExpenseError(
                f"La respuesta de la IA no pudo ser interpretada como JSON válido: {str(err)}"
            ) from err

    async def extract_expense_from_ocr(
        self, request: OcrExpenseExtractRequest
    ) -> AiExpenseExtractResponse:
        """
        Envía el texto OCR al modelo local Ollama y valida la salida con Pydantic.
        """
        start_time = time.perf_counter()

        # Determinar período por defecto
        now = datetime.now()
        default_period = request.period_key or f"{now.year:04d}-{now.month:02d}"

        user_prompt = (
            f"Texto OCR del documento:\n"
            f"---\n"
            f"{request.raw_text.strip()}\n"
            f"---\n\n"
            f"Período sugerido: {default_period}\n"
            f"Fecha actual de referencia: {now.strftime('%Y-%m-%d')}\n"
            f"Estructura el gasto adicional en JSON respetando las 10 categorías oficiales."
        )

        ollama_payload = {
            "model": self.model,
            "prompt": user_prompt,
            "system": self.SYSTEM_PROMPT,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,
            },
        }

        endpoint_url = f"{self.base_url}/api/generate"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(endpoint_url, json=ollama_payload)
                response.raise_for_status()
                data = response.json()
        except httpx.ConnectError as err:
            raise AiConnectionError(
                f"No se pudo conectar con el servidor de IA Ollama en {self.base_url}. "
                "Verifique que el servicio esté activo y accesible."
            ) from err
        except httpx.TimeoutException as err:
            raise AiTimeoutError(
                f"La solicitud al modelo de IA excedió el tiempo límite de {self.timeout_seconds} segundos."
            ) from err
        except httpx.HTTPStatusError as err:
            raise AiServiceError(
                f"El servidor Ollama respondió con error HTTP {err.response.status_code}: {err.response.text}"
            ) from err
        except Exception as err:
            raise AiServiceError(f"Error inesperado al consultar el modelo de IA: {str(err)}") from err

        raw_ai_text = data.get("response", "")
        if not raw_ai_text:
            raise AiUnprocessableExpenseError("El modelo de IA retornó una respuesta vacía.")

        parsed_dict = self._sanitize_json_response(raw_ai_text)

        # Verificar si el modelo reportó explícitamente incapacidad de extraer gasto
        if parsed_dict.get("error") == "unextractable_expense":
            raise AiUnprocessableExpenseError(
                "El texto del documento no contiene información financiera suficiente para registrar un gasto adicional."
            )

        # Garantizar período si no vino en la respuesta
        if not parsed_dict.get("periodKey"):
            parsed_dict["periodKey"] = default_period

        # Validar y normalizar a través de Pydantic
        try:
            expense_payload = AdditionalExpensePayload(**parsed_dict)
        except ValidationError as err:
            raise AiUnprocessableExpenseError(
                f"Los datos extraídos no satisfacen el contrato de gasto adicional: {err.errors()}"
            ) from err

        processing_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return AiExpenseExtractResponse(
            success=True,
            expense=expense_payload,
            processing_time_ms=processing_time_ms,
            model=self.model,
            message="Gasto adicional extraído y validado exitosamente.",
        )


ai_expense_service = AiExpenseService()
