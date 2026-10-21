from typing import List, Set
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "CyclePay Backend"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # Ollama AI Settings
    OLLAMA_BASE_URL: str = "http://192.168.0.148:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:3b"
    OLLAMA_TIMEOUT_SECONDS: float = 60.0

    # OCR Settings & Resource Optimization (Optimizado para Raspberry Pi 5 / Dokploy)
    OCR_ENGINE: str = "auto"  # 'auto', 'tesseract' o 'easyocr'
    OCR_NUM_THREADS: int = 4
    EASYOCR_CANVAS_SIZE: int = 1280
    IMAGE_MAX_DIMENSION: int = 1600
    MAX_IMAGE_SIZE_MB: int = 10
    ALLOWED_IMAGE_EXTENSIONS: Set[str] = {".png", ".jpg", ".jpeg", ".webp"}


settings = Settings()
