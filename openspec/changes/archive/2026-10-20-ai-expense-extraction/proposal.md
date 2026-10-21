## Why

El backend cuenta con el endpoint de OCR (`/api/v1/ocr/extract-text`) para digitalizar facturas y recibos en texto plano. Sin embargo, los usuarios necesitan convertir automáticamente dicho texto no estructurado en una entidad de gasto lista para registrarse en CyclePay sin transcripción manual.

## What Changes

- Nuevo servicio de integración asíncrona con el modelo de IA local (Ollama en `http://192.168.0.148:11434` o configurable vía settings).
- Nuevo endpoint `POST /api/v1/ai/extract-expense` que recibe el texto plano (o salida OCR) y ejecuta inferencia con salida JSON estructurada y validada con Pydantic v2.
- Inferencia de campos de gasto adicional: nombre del comercio/emisor, monto numérico, categorización estricta (1 de las 10 categorías permitidas), día de vencimiento/emisión (1–31), período (`YYYY-MM`), descripción concisa (máximo 140 caracteres) y estado (`pending` o `paid`).
- Manejo robusto de errores de conectividad con Ollama, timeouts y fallback ante documentos sin datos financieros claros.

## Non-goals

- No genera ni soporta plantillas recurrentes (`ExpenseTemplate`); el feature está enfocado exclusivamente en gastos adicionales puntuales (`MonthlyExpense` / `CreateManualExpenseInput`).
- No almacena en base de datos; la persistencia final sigue perteneciendo al cliente frontend en Firestore.
- No reemplaza el endpoint de OCR existente; opera como una etapa desacoplada que consume el texto extraído.

## Capabilities

### New Capabilities
- `expense-extraction`: Inferencia con modelo de IA y estructuración de gastos adicionales a partir del texto OCR conforme al contrato frontend de CyclePay.

### Modified Capabilities
<!-- Ninguna especificación existente cambia sus requisitos -->

## Impact

- **Módulos tocados**:
  - `app/core/config.py`: Variables de configuración para Ollama (URL del host, modelo, timeout).
  - `app/schemas/ai.py`: Schemas de request (`OcrExpenseExtractRequest`) y response (`ExtractedExpenseResponse`) compatibles con `CreateManualExpenseInput`.
  - `app/services/ai_service.py`: Lógica de llamada HTTP a Ollama con prompt estructurado, parseo y validación Pydantic.
  - `app/api/v1/endpoints/ai.py` y `app/api/v1/api.py`: Exposición del nuevo router en `/api/v1/ai`.
- **Compatibilidad**:
  - 100% compatible con el contrato frontend `CreateManualExpenseInput`: categorías estrictas (`Vivienda`, `Servicios`, `Alimentación`, `Transporte`, `Salud`, `Educación`, `Entretenimiento`, `Seguros`, `Suscripciones`, `Otros`), montos > 0 y período `YYYY-MM`.
- **Dependencias**:
  - `httpx` (ya presente en `requirements.txt`).
