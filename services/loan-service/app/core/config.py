from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    # Core (ADD THESE → FIXES YOUR ERROR)
    SERVICE_NAME: Optional[str] = "service"
    PORT: Optional[int] = 8000
    ENVIRONMENT: Optional[str] = "development"
    API_PREFIX: str = "/api"

    # Mongo
    MONGO_URI: Optional[str] = None
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: Optional[str] = None
    MONGODB_DB: str = "pay_crest"

    # JWT
    SECRET_KEY: Optional[str] = None
    JWT_SECRET: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Service URLs
    AUTH_SERVICE_URL: Optional[str] = None
    LOAN_SERVICE_URL: Optional[str] = None
    EMI_SERVICE_URL: Optional[str] = None
    WALLET_SERVICE_URL: Optional[str] = None
    PAYMENT_SERVICE_URL: Optional[str] = None
    VERIFICATION_SERVICE_URL: Optional[str] = None
    ADMIN_SERVICE_URL: Optional[str] = None
    MANAGER_SERVICE_URL: Optional[str] = None

    # Cashfree
    CASHFREE_ENV: str = "sandbox"
    CASHFREE_CLIENT_ID: Optional[str] = None
    CASHFREE_CLIENT_SECRET: Optional[str] = None
    
    UPLOAD_BASE_PATH: str = "./uploads"

    # ✅ IMPORTANT FIX
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"   # 🔥 THIS FIXES YOUR ERROR
    )


settings = Settings()