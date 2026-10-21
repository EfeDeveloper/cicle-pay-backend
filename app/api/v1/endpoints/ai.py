from fastapi import APIRouter, HTTPException, status
from app.schemas.ai import AiExpenseExtractResponse, OcrExpenseExtractRequest
from app.services.ai_service import (
    AiConnectionError,
    AiServiceError,
    AiTimeoutError,
    AiUnprocessableExpenseError,
    ai_expense_service,
)

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post(
    "/extract-expense",
    response_model=AiExpenseExtractResponse,
    status_code=status.HTTP_200_OK,
    summary="Extraer gasto adicional estructurado desde texto OCR",
    description=(
        "Recibe texto plano extraído de una factura o comprobante y consulta al modelo de IA (Ollama) "
        "para inferir y validar un gasto adicional conforme al contrato CreateManualExpenseInput de CyclePay."
    ),
    responses={
        200: {
            "description": "Gasto adicional extraído y validado exitosamente",
            "model": AiExpenseExtractResponse,
        },
        422: {
            "description": "El texto OCR no contiene datos suficientes o válidos para registrar un gasto",
        },
        503: {
            "description": "El servidor de IA (Ollama) no está disponible o excedió el tiempo límite",
        },
    },
)
async def extract_additional_expense_from_ocr(
    request: OcrExpenseExtractRequest,
) -> AiExpenseExtractResponse:
    try:
        result = await ai_expense_service.extract_expense_from_ocr(request)
        return result
    except AiConnectionError as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(err),
        ) from err
    except AiTimeoutError as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(err),
        ) from err
    except AiUnprocessableExpenseError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        ) from err
    except AiServiceError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(err),
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado al procesar la extracción con IA: {str(err)}",
        ) from err
