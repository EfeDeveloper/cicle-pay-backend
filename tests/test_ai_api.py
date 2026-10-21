import json
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def make_ollama_mock_response(response_dict_or_str, status_code: int = 200) -> httpx.Response:
    """Helper para crear una respuesta HTTP simulada de Ollama."""
    if isinstance(response_dict_or_str, dict):
        response_text = json.dumps(response_dict_or_str)
    else:
        response_text = response_dict_or_str

    payload = {
        "model": "qwen2.5-coder:3b",
        "response": response_text,
        "done": True,
        "total_duration": 1200000000,
    }
    return httpx.Response(
        status_code=status_code,
        json=payload,
        request=httpx.Request("POST", "http://test/api/generate"),
    )


def test_extract_expense_success():
    """Verifica que un texto OCR válido se transforme en un gasto adicional de CyclePay."""
    mock_llm_output = {
        "name": "Supermercado Éxito",
        "amount": 145000.0,
        "category": "Alimentación",
        "description": "Compra de despensa quincenal",
        "dueDay": 15,
        "periodKey": "2026-10",
        "status": "paid",
    }

    mock_resp = make_ollama_mock_response(mock_llm_output)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        response = client.post(
            "/api/v1/ai/extract-expense",
            json={
                "raw_text": "SUPERMERCADO EXITO S.A. \nFECHA: 15/10/2026 \nTOTAL: $145.000 \nPAGO: TARJETA DEBITO",
                "period_key": "2026-10",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "expense" in data
    expense = data["expense"]
    assert expense["name"] == "Supermercado Éxito"
    assert expense["amount"] == 145000.0
    assert expense["category"] == "Alimentación"
    assert expense["dueDay"] == 15
    assert expense["periodKey"] == "2026-10"
    assert expense["status"] == "paid"
    assert expense["source"] == "manual"
    assert expense["templateId"] is None
    assert data["processing_time_ms"] > 0


def test_extract_expense_markdown_codeblock():
    """Verifica que la sanitización extraiga el JSON aun si el modelo lo envuelve en markdown."""
    raw_markdown = """```json
    {
        "name": "Droguería La Rebaja",
        "amount": 35200.0,
        "category": "Salud",
        "description": "Medicamentos recetados",
        "dueDay": 12,
        "periodKey": "2026-10",
        "status": "paid"
    }
    ```"""

    mock_resp = make_ollama_mock_response(raw_markdown)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        response = client.post(
            "/api/v1/ai/extract-expense",
            json={"raw_text": "DROGUERIA LA REBAJA TOTAL: $35.200"},
        )

    assert response.status_code == 200
    expense = response.json()["expense"]
    assert expense["name"] == "Droguería La Rebaja"
    assert expense["amount"] == 35200.0
    assert expense["category"] == "Salud"


def test_extract_expense_category_normalization():
    """Verifica que categorías no canónicas se normalicen a las 10 categorías oficiales."""
    mock_llm_output = {
        "name": "Restaurante El Corral",
        "amount": 42000.0,
        "category": "comida",
        "dueDay": None,
        "periodKey": "2026-10",
        "status": "paid",
    }

    mock_resp = make_ollama_mock_response(mock_llm_output)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        response = client.post(
            "/api/v1/ai/extract-expense",
            json={"raw_text": "RESTAURANTE EL CORRAL TOTAL: $42.000"},
        )

    assert response.status_code == 200
    expense = response.json()["expense"]
    assert expense["category"] == "Alimentación"


def test_extract_expense_service_unavailable():
    """Verifica HTTP 503 cuando Ollama no está accesible en la red."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        response = client.post(
            "/api/v1/ai/extract-expense",
            json={"raw_text": "Recibo de prueba"},
        )

    assert response.status_code == 503
    assert "no se pudo conectar" in response.json()["detail"].lower()


def test_extract_expense_timeout():
    """Verifica HTTP 503 cuando Ollama excede el tiempo límite."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Read timed out")

        response = client.post(
            "/api/v1/ai/extract-expense",
            json={"raw_text": "Recibo de prueba"},
        )

    assert response.status_code == 503
    assert "tiempo límite" in response.json()["detail"].lower()


def test_extract_expense_unextractable_text():
    """Verifica HTTP 422 cuando el texto no contiene datos financieros."""
    mock_resp = make_ollama_mock_response({"error": "unextractable_expense"})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        response = client.post(
            "/api/v1/ai/extract-expense",
            json={"raw_text": "Texto aleatorio sin compras ni valores."},
        )

    assert response.status_code == 422
    assert "no contiene información financiera" in response.json()["detail"].lower()


def test_extract_expense_invalid_amount_rejected():
    """Verifica HTTP 422 cuando el monto extraído no es un número positivo."""
    mock_llm_output = {
        "name": "Comercio Inválido",
        "amount": -500.0,
        "category": "Otros",
        "periodKey": "2026-10",
    }
    mock_resp = make_ollama_mock_response(mock_llm_output)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        response = client.post(
            "/api/v1/ai/extract-expense",
            json={"raw_text": "Recibo inválido"},
        )

    assert response.status_code == 422
