# Change: Ingesta de Imágenes y Extracción OCR Inicial

## Why

CyclePay requiere permitir a los usuarios digitalizar comprobantes, recibos y facturas de servicios sin ingresar los datos manualmente. El primer paso técnico fundamental es proveer un endpoint capaz de recibir una imagen, procesarla con una biblioteca OCR en Python (sin dependencias a nivel de sistema host), y retornar el texto extraído o un mensaje claro cuando el documento no contenga texto legible.

## What Changes

- Creación de la arquitectura base de la aplicación FastAPI (`app/main.py`, `app/core/config.py`, `app/api/v1/`).
- Endpoint `POST /api/v1/ocr/extract-text` que recibe archivos de imagen (`multipart/form-data`) en formatos comunes (PNG, JPEG, JPG, WEBP).
- Servicio OCR modular en `app/services/ocr_service.py` que preprocesa la imagen y extrae líneas de texto legibles.
- Validación del resultado de la extracción:
  - Si la imagen contiene texto legible, retorna las líneas de texto extraídas y metadata de ejecución (tiempo en ms, recuento de líneas).
  - Si la imagen no contiene texto legible (o está en blanco/ilegible), retorna un mensaje informativo indicando que no se detectó texto en el comprobante.
- Endpoint de verificación de salud del backend `GET /api/v1/health`.

## Non-goals

- **Integración con modelos de IA / Ollama**: Se omite deliberadamente en esta propuesta; será objeto de un cambio OpenSpec posterior enfocado en la estructuración semántica hacia los contratos de CyclePay.
- **Escritura directa a base de datos (Firestore)**: El backend actúa como procesador de datos; la persistencia final la gestiona el frontend de CyclePay.
- **Dependencias de software a nivel de SO**: No se utilizan instaladores de sistema tipo Homebrew; toda la funcionalidad se resuelve mediante librerías de Python compatibles con contenedores Dokploy / Linux.

## Capabilities

### New Capabilities

- `ocr-ingestion`: Recepción de imágenes de facturas/comprobantes, preprocesamiento y extracción OCR de texto crudo con detección de documentos sin texto.

### Modified Capabilities

*(Ninguna, es la primera capacidad del repositorio)*

## Impact

- **Código:** Nuevos módulos en `app/api/v1/endpoints/ocr.py`, `app/services/ocr_service.py`, `app/schemas/ocr.py`.
- **APIs:** Nuevos endpoints `POST /api/v1/ocr/extract-text` y `GET /api/v1/health`.
- **Dependencias:** `fastapi`, `uvicorn`, `pydantic`, `pillow`, `python-multipart`.
