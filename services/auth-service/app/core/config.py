from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Core
    SERVICE_NAME: Optional[str] = "auth-service"
    API_PREFIX: str = "/api"
    PORT: Optional[int] = 3001
    ENVIRONMENT: Optional[str] = "development"
    DEFAULT_IFSC: str = "TEST0001234"

    # Mongo
    MONGO_URI: Optional[str] = None
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: Optional[str] = None
    MONGODB_DB: str = "pay_crest"

    # JWT
    SECRET_KEY: Optional[str] = None
    JWT_SECRET_KEY: str  # This is the required field causing the error
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 
    ALGORITHM: Optional[str] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: Optional[int] = 60

    # Service URLs
    AUTH_SERVICE_URL: Optional[str] = None
    LOAN_SERVICE_URL: Optional[str] = None
    EMI_SERVICE_URL: Optional[str] = None
    WALLET_SERVICE_URL: Optional[str] = None
    PAYMENT_SERVICE_URL: Optional[str] = None
    VERIFICATION_SERVICE_URL: Optional[str] = None
    ADMIN_SERVICE_URL: Optional[str] = None
    MANAGER_SERVICE_URL: Optional[str] = None

    # ✅ THIS MUST BE INSIDE THE CLASS INDENTATION
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra="allow"
    )

# Now it will correctly load the variables from .env
settings = Settings()