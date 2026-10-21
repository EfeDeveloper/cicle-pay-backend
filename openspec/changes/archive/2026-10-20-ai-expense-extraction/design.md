## Context

El backend dispone de un módulo OCR (`/api/v1/ocr/extract-text`) que extrae texto plano a partir de imágenes de recibos y facturas. Para completar el flujo sin requerir digitación manual, se necesita un servicio que interprete semánticamente ese texto plano y genere una estructura válida según el contrato de gastos adicionales de CyclePay (`CreateManualExpenseInput`). Ver `proposal.md` para el contexto de negocio.

## Goals / Non-Goals

**Goals:**
- Crear el servicio `AiExpenseService` usando `httpx.AsyncClient` para interactuar de forma asíncrona y no bloqueante con Ollama (`/api/generate` o `/api/chat` con `format: "json"`).
- Diseñar schemas Pydantic v2 en `app/schemas/ai.py` que modelen el request (`OcrExpenseExtractRequest`) y el response (`AiExpenseExtractResponse`), garantizando la validez de tipos: monto numérico positivo, día 1–31 o null, formato de período `YYYY-MM` y una de las 10 categorías oficiales.
- Exponer el endpoint `POST /api/v1/ai/extract-expense` bajo el router `/api/v1/ai`.
- Configurar variables de entorno en `app/core/config.py`: `OLLAMA_BASE_URL`, `OLLAMA_MODEL` y `OLLAMA_TIMEOUT_SECONDS`.
- Proveer sanitización de salida del LLM (extracción de JSON si el modelo incluye bloques markdown) y manejo robusto de excepciones (HTTP 503 ante caída de Ollama, HTTP 422 ante texto sin datos financieros).

**Non-Goals:**
- Ningún soporte para plantillas (`ExpenseTemplate`); el feature está restringido con exclusividad a gastos adicionales puntuales.
- Persistencia en base de datos (el cliente frontend gestiona el guardado en Firestore).
- Modificación del motor OCR existente.

## Decisions

### Decisión 1: Integración directa vía HTTP REST con Ollama usando `httpx.AsyncClient`
- **Elección**: Llamar a la API REST nativa de Ollama (`POST /api/generate` con `"format": "json"` y `"stream": false`) usando `httpx.AsyncClient`.
- **Por qué**: Evita dependencias pesadas como LangChain, LlamaIndex o SDKs externos. Respeta la regla de cero dependencias binarias o locks innecesarios.
- **Alternativas consideradas**:
  - *LangChain / Instructor*: Añaden capas innecesarias de complejidad y dependencias transitivas para una única llamada estructurada.
  - *Llamadas síncronas (`requests`)*: Bloquearían el event loop de FastAPI durante los segundos de inferencia del LLM.

### Decisión 2: Endpoints desacoplados (OCR separado de AI)
- **Elección**: Mantener `/api/v1/ocr/extract-text` y crear `/api/v1/ai/extract-expense` de forma independiente.
- **Por qué**: Permite que el frontend o cliente muestre primero el texto extraído al usuario para revisión/edición previa si lo desea, facilita pruebas unitarias aisladas sin procesar imágenes reales, y desacopla los ciclos de vida del motor OCR y del servidor de inferencia.
- **Alternativas consideradas**:
  - *Endpoint monolítico `/api/v1/ocr/process-expense`*: Obligaría a ejecutar OCR + IA en un único request largo, dificultando reintentos ante fallos específicos de IA.

### Decisión 3: Validación estricta con Pydantic v2 y normalización de categorías
- **Elección**: Definir un Enum / Literal de Pydantic con las 10 categorías permitidas (`Vivienda`, `Servicios`, `Alimentación`, `Transporte`, `Salud`, `Educación`, `Entretenimiento`, `Seguros`, `Suscripciones`, `Otros`). Si el modelo responde una variante cercana (e.g. minúsculas o sin acento), un validador en Pydantic normaliza al valor canónico; si es inválida, hace fallback a `Otros`.
- **Por qué**: Garantiza que el frontend nunca reciba categorías incompatibles con las reglas de negocio de CyclePay.

### Decisión 4: Prompt semántico con Few-Shot / Constraints explícitos
- **Elección**: Diseñar un system prompt conciso en `app/services/ai_service.py` que obligue a responder exclusivamente en JSON con las claves exactas: `name`, `amount`, `category`, `description`, `dueDay`, `periodKey`, `status`.
- **Por qué**: Los modelos ligeros (como `qwen2.5-coder:3b`) operan con mayor precisión cuando se les proporciona el esquema JSON esperado y las opciones restringidas en el prompt.

## Risks / Trade-offs

- **[Riesgo: Latencia de inferencia en Raspberry Pi / CPU]** → *Mitigación*: Inferencia asíncrona no bloqueante con `httpx.AsyncClient`, timeout configurable (`OLLAMA_TIMEOUT_SECONDS=30`) y uso de modelos ligeros cuantizados (`qwen2.5-coder:3b` o `llama3.2:3b`).
- **[Riesgo: Ollama no disponible en la red local]** → *Mitigación*: Captura de `httpx.ConnectError` y `httpx.TimeoutException` transformándolas en HTTP 503 con mensaje claro para el usuario.
- **[Riesgo: Texto OCR ilegible o sin información de gasto]** → *Mitigación*: Detección de respuesta vacía o montos no identificados, retornando HTTP 422 descriptivo en lugar de generar gastos ficticios con monto cero.
- **[Riesgo: Formato de fecha / período ausente]** → *Mitigación*: Si el documento no incluye fecha, se permite enviar `default_period_key` en el request o fallback al mes corriente (`YYYY-MM`), con `dueDay: null`.
