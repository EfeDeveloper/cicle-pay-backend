import io
from unittest.mock import patch
from PIL import Image, ImageDraw
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def create_in_memory_image(text: str = "", format: str = "PNG") -> bytes:
    """Helper para crear una imagen en memoria."""
    img = Image.new("RGB", (300, 150), color="white")
    if text:
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), text, fill="black")
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    return buffer.getvalue()


def test_health_endpoint():
    """Verifica que el endpoint de salud responde correctamente."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "CyclePay Backend"
    assert "version" in data


def test_reject_unsupported_extension():
    """Verifica que se rechacen archivos con extensiones no permitidas (ej: .txt, .pdf)."""
    response = client.post(
        "/api/v1/ocr/extract-text",
        files={"file": ("factura.txt", b"Texto de prueba", "text/plain")},
    )
    assert response.status_code == 400
    assert "no soportado" in response.json()["detail"].lower()


def test_reject_corrupted_image():
    """Verifica que se rechace un archivo con extensión válida pero bytes corruptos."""
    response = client.post(
        "/api/v1/ocr/extract-text",
        files={"file": ("comprobante.png", b"NOT_A_VALID_IMAGE_BYTES", "image/png")},
    )
    assert response.status_code == 400
    assert "inválido o corrupto" in response.json()["detail"].lower()


def test_blank_image_returns_no_text_response():
    """Verifica que una imagen en blanco devuelva has_text: False con mensaje descriptivo."""
    blank_bytes = create_in_memory_image(text="", format="PNG")
    response = client.post(
        "/api/v1/ocr/extract-text",
        files={"file": ("blanco.png", blank_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["has_text"] is False
    assert data["line_count"] == 0
    assert data["raw_text"] == ""
    assert data["lines"] == []
    assert data["message"] == "No se detectó texto legible en el documento"
    assert data["processing_time_ms"] >= 0


def test_image_with_text_extraction():
    """Verifica el flujo exitoso cuando se detecta texto en la imagen."""
    image_bytes = create_in_memory_image(text="ENEL COLOMBIA", format="PNG")
    simulated_ocr_lines = [
        "ENEL COLOMBIA S.A. ESP",
        "TOTAL A PAGAR: $125.000",
        "PAGO OPORTUNO: 15/11/2026",
    ]

    with patch("app.services.ocr_service.OcrService._extract_text", return_value=simulated_ocr_lines):
        response = client.post(
            "/api/v1/ocr/extract-text",
            files={"file": ("factura_enel.png", image_bytes, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_text"] is True
        assert data["line_count"] == 3
        assert "ENEL COLOMBIA" in data["raw_text"]
        assert len(data["lines"]) == 3
        assert data["lines"][0] == "ENEL COLOMBIA S.A. ESP"
        assert data["message"] is None
        assert data["processing_time_ms"] >= 0


def test_extract_text_real_fixture_image():
    """Prueba de integración end-to-end con una imagen de recibo real almacenada en el repositorio."""
    from pathlib import Path
    sample_path = Path(__file__).parent / "fixtures" / "sample_receipt.png"
    assert sample_path.exists(), f"El archivo de prueba {sample_path} debe existir en el repositorio."

    with open(sample_path, "rb") as f:
        response = client.post(
            "/api/v1/ocr/extract-text",
            files={"file": ("sample_receipt.png", f, "image/png")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["has_text"] is True
    assert data["line_count"] >= 5
    assert "pago" in data["raw_text"].lower()
    assert data["message"] is None
    assert data["processing_time_ms"] > 0

