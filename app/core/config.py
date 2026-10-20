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

    # OCR Settings
    OCR_ENGINE: str = "auto"
    MAX_IMAGE_SIZE_MB: int = 10
    ALLOWED_IMAGE_EXTENSIONS: Set[str] = {".png", ".jpg", ".jpeg", ".webp"}


settings = Settings()
