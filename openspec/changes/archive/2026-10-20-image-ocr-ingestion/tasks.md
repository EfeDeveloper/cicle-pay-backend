## 1. Base Framework & Schemas

- [x] 1.1 [dev] Configurar estructura de directorios modular `app/` (`core`, `api/v1/endpoints`, `schemas`, `services`) y verificar presencia de `__init__.py`
- [x] 1.2 [dev] Implementar configuración centralizada `app/core/config.py` con `pydantic-settings` y verificar que carga variables de `.env`
- [x] 1.3 [dev] Implementar esquemas de respuesta OCR en `app/schemas/ocr.py` (`OcrTextResponse`) con campos `has_text`, `raw_text`, `lines`, `line_count`, `message` y `processing_time_ms`
- [x] 1.4 [dev] Configurar aplicación FastAPI `app/main.py` con middleware CORS para CyclePay y router `/api/v1` incluyendo endpoint `GET /api/v1/health`

## 2. OCR Service & Preprocessing

- [x] 2.1 [dev] Implementar módulo de preprocesamiento de imágenes con Pillow en `app/services/image_preprocessor.py` (redimensionamiento, conversión a escala de grises y normalización)
- [x] 2.2 [dev] Implementar servicio de extracción OCR en `app/services/ocr_service.py` con soporte para reconocimiento de texto y manejo de imágenes sin texto

## 3. Endpoints & Pruebas Automatizadas

- [x] 3.1 [dev] Implementar endpoint `POST /api/v1/ocr/extract-text` en `app/api/v1/endpoints/ocr.py` con validación de formato de archivo (PNG, JPG, JPEG, WEBP) y retorno estructurado
- [x] 3.2 [test] Crear suite de pruebas con pytest en `tests/test_ocr_api.py` cubriendo: subida de imagen con texto, imagen en blanco/sin texto (`has_text: false`) y rechazo de archivo no permitido (HTTP 400)
- [x] 3.3 [test] Ejecutar `pytest` en el entorno `.venv` y verificar que el 100% de las pruebas estén en verde
