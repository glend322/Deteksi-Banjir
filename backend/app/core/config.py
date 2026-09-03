from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
import json
from pydantic import field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "SafeRoute API"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = "saferoute-semarang-super-secret-jwt-key-2026-hackathon"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    ALGORITHM: str = "HS256"

    DATABASE_URL: str = "postgresql://postgres:postgrespassword@localhost:5432/saferoute_db"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        elif isinstance(v, list):
            return v
        return ["*"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

