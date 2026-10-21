## 1. Configuración y Esquemas de Datos

- [x] 1.1 [dev] Añadir configuración de Ollama (`OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`) en `app/core/config.py` y `.env.example`, y verificar que los settings carguen correctamente con valores por defecto y desde variables de entorno.
- [x] 1.2 [dev] Implementar schemas Pydantic v2 en `app/schemas/ai.py` (`OcrExpenseExtractRequest`, `AdditionalExpensePayload`, `AiExpenseExtractResponse`) con validación estricta de las 10 categorías de CyclePay, montos mayores a 0, período `YYYY-MM` y `dueDay` 1–31 o null, verificando su comportamiento con validadores unitarios.

## 2. Servicio de Integración con IA

- [x] 2.1 [dev] Crear `app/services/ai_service.py` implementando la llamada asíncrona con `httpx.AsyncClient` al endpoint `/api/generate` de Ollama con formato JSON y system prompt especializado en gastos adicionales.
- [x] 2.2 [dev] Implementar sanitización de respuestas JSON (extracción de markdown codeblocks) y manejo de excepciones de red (`ConnectError`, `TimeoutException`) y respuestas no estructurables en `AiExpenseService`.

## 3. Endpoints de API y Rutas

- [x] 3.1 [dev] Crear `app/api/v1/endpoints/ai.py` exponiendo `POST /api/v1/ai/extract-expense`, documentando códigos HTTP (200, 422, 503), y registrar el router en `app/api/v1/api.py`.
- [x] 3.2 [test] Crear suite de pruebas en `tests/test_ai_api.py` usando `pytest-asyncio` y mocks de `httpx` para verificar extracción exitosa, normalización de categorías, error por indisponibilidad de Ollama (503) y texto sin datos válidos (422).

## 4. Verificación de Integración

- [x] 4.1 [test] Ejecutar la suite completa de pruebas del backend con `pytest` y verificar que todas las pruebas (OCR existente y nuevo flujo de IA) pasen al 100%.
