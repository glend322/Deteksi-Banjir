import logging
import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
import json
from pydantic import field_validator, model_validator

logger = logging.getLogger(__name__)

# Known insecure defaults — refuse to use in production
_INSECURE_SECRETS = {
    "saferoute-semarang-super-secret-jwt-key-2026-hackathon",
    "internal-saferoute-ai-key-2026",
    "replace-with-a-secure-random-32-character-secret",
    "replace-with-internal-api-key",
}


class Settings(BaseSettings):
    PROJECT_NAME: str = "SafeRoute API"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    ALGORITHM: str = "HS256"

    DATABASE_URL: str = "postgresql://postgres:postgrespassword@localhost:5432/saferoute_db"

    # OSRM Routing Engine (100% Free & Open Source)
    OSRM_BASE_URL: str = "http://router.project-osrm.org"
    ROUTING_TIMEOUT_SECONDS: float = 4.0

    # AI / ML Modeling Service
    MODELING_API_URL: str = "http://localhost:8001"

    # Internal API Key untuk endpoint AI Bridge (diisi via .env)
    INTERNAL_API_KEY: str = ""

    # Firebase Cloud Messaging (FCM)
    FIREBASE_CREDENTIALS_PATH: str = ""  # Path to serviceAccountKey.json

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

    @model_validator(mode="after")
    def _warn_insecure_defaults(self) -> "Settings":
        if not self.SECRET_KEY or self.SECRET_KEY in _INSECURE_SECRETS:
            self.SECRET_KEY = secrets.token_urlsafe(48)
            logger.warning(
                "[SECURITY] SECRET_KEY not set or using insecure default — "
                "generated a random key. Set SECRET_KEY in .env for stable JWTs."
            )

        if not self.INTERNAL_API_KEY or self.INTERNAL_API_KEY in _INSECURE_SECRETS:
            self.INTERNAL_API_KEY = secrets.token_urlsafe(32)
            logger.warning(
                "[SECURITY] INTERNAL_API_KEY not set or using insecure default — "
                "generated a random key. Set INTERNAL_API_KEY in .env for stable AI bridge auth."
            )

        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
