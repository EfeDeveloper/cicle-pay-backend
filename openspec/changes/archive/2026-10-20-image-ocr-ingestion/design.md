# Design: Ingesta de Imágenes y Extracción OCR Inicial

## Context

El backend de CyclePay requiere procesar imágenes de facturas y recibos subidos por usuarios. El diseño debe garantizar modularidad, extensibilidad para futuros módulos y compatibilidad total con despliegues en contenedores Dokploy / Linux sin amarrar dependencias a gestores de paquetes del host local (como Homebrew).

## Goals / Non-Goals

**Goals:**
- Estructurar el backend en FastAPI con arquitectura desacoplada (`core`, `api`, `schemas`, `services`).
- Proveer un endpoint robusto para subir imágenes vía `multipart/form-data`.
- Ejecutar extracción OCR modular usando Pillow para preprocesamiento y limpieza de imagen.
- Entregar respuestas estructuradas que distingan claramente entre documentos con texto reconocido y documentos en blanco/sin texto legible.

**Non-Goals:**
- Inferencia con modelos de lenguaje (Ollama) en esta fase (se abordará en el siguiente cambio OpenSpec).
- Persistencia de base de datos o almacenamiento en la nube de imágenes (las imágenes se procesan en memoria o buffer efímero).

## Decisions

### 1. Arquitectura modular de endpoints y servicios
- **Decisión:** Separar la capa HTTP (`app/api/v1/endpoints/ocr.py`) de la lógica de procesamiento (`app/services/ocr_service.py`) y los modelos (`app/schemas/ocr.py`).
- **Alternativas consideradas:** Escribir la lógica directamente en las rutas de FastAPI.
- **Razón:** Permite que en futuras propuestas el servicio de IA consuma directamente el `ocr_service` sin acoplarse a peticiones HTTP.

### 2. Preprocesamiento de imagen con Pillow
- **Decisión:** Usar `Pillow` para normalizar tamaño, convertir a escala de grises y aumentar contraste antes de enviar los datos al motor OCR.
- **Alternativas consideradas:** Procesar bytes crudos directamente.
- **Razón:** El preprocesamiento mejora notablemente la tasa de acierto en fotos de tickets y recibos arrugados o de baja luminosidad.

### 3. Manejo de dependencias y despliegue Dokploy
- **Decisión:** Envolver el acceso al motor OCR con tolerancia a fallos y configuración de entorno (`OCR_ENGINE`). En producción Docker (Dokploy), el contenedor proveerá el motor OCR de forma aislada sin requerir instalaciones en el sistema operativo anfitrión del desarrollador.

### 4. Estructura de respuesta de la API
- **Decisión:** Usar un schema Pydantic explícito:
  ```python
  class OcrExtractionResult(BaseModel):
      has_text: bool
      raw_text: str
      lines: list[str]
      line_count: int
      message: Optional[str] = None
      processing_time_ms: float
  ```
- **Razón:** El cliente consumidor recibe inmediatamente el estado de lectura sin ambigüedades.

## Risks / Trade-offs

- [Calidad variable de imágenes de facturas] → Mitigación: Preprocesamiento de imagen y retorno de mensaje claro cuando no se detecte texto legible.
- [Tamaño de imágenes grandes causando latencia] → Mitigación: Validación de tamaño máximo de archivo y redimensionamiento inteligente en memoria si excede dimensiones estándar.
