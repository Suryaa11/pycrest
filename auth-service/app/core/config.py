from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator
from typing import Optional


class Settings(BaseSettings):
    SERVICE_NAME: Optional[str] = "auth-service"
    API_PREFIX: str = "/api"
    PORT: Optional[int] = 3001
    ENVIRONMENT: Optional[str] = "development"
    DEFAULT_IFSC: str = "TEST0001234"

    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "pycrest"

    JWT_SECRET: str = "CHANGE_ME"
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    ALGORITHM: Optional[str] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: Optional[int] = 60

    IDEMPOTENCY_ENABLED: bool = True
    IDEMPOTENCY_TTL_HOURS: int = 24

    INTERNAL_SERVICE_TOKEN: str = "CHANGE_ME"
    UPLOAD_BASE_PATH: str = "./uploads"

    AUTH_SERVICE_URL: Optional[str] = None
    LOAN_SERVICE_URL: Optional[str] = None
    EMI_SERVICE_URL: Optional[str] = None
    WALLET_SERVICE_URL: Optional[str] = None
    PAYMENT_SERVICE_URL: Optional[str] = None
    VERIFICATION_SERVICE_URL: Optional[str] = None
    ADMIN_SERVICE_URL: Optional[str] = None
    MANAGER_SERVICE_URL: Optional[str] = None

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

    def model_post_init(self, __context):
        if self.JWT_SECRET == "CHANGE_ME" and self.JWT_SECRET_KEY:
            object.__setattr__(self, "JWT_SECRET", self.JWT_SECRET_KEY)


settings = Settings()