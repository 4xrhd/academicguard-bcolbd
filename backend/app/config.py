"""
config.py — Application settings loaded from environment variables.
All thresholds (risk score boundaries, weighting coefficients) are
configurable here without requiring code re-deployment.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ───────────────────────────────────────────────
    APP_NAME: str = "AcademicGuard"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    FRONTEND_ORIGIN: str = "https://academicguard.example.com"

    # ── Database & Cache ──────────────────────────────────────────
    DATABASE_URL: str = ""  # e.g. postgresql+psycopg2://user:pass@db:5432/academicguard
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Security ──────────────────────────────────────────────────
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12
    TRUSTED_PROXIES: str = "127.0.0.1"
    SECURE_COOKIES: bool = True

    # ── File Upload ───────────────────────────────────────────────
    UPLOAD_DIR: str = "/app/uploads"
    EXPORT_DIR: str = "/app/exports"
    MAX_FILE_SIZE_MB: int = 10
    MAX_FILES_PER_BATCH: int = 60

    # ── Risk Score Thresholds (tunable) ──────────────────────────
    RISK_HIGH_THRESHOLD: float = 0.70
    RISK_MEDIUM_THRESHOLD: float = 0.40

    # ── Risk Score Weights (must sum to 1.0) ─────────────────────
    # Whitepaper §4 Code-Present Profile: 0.40 AI + 0.35 TextSim + 0.25 CodeSim
    WEIGHT_TEXT_SIM: float = 0.35
    WEIGHT_CODE_SIM: float = 0.25
    WEIGHT_AI_PROB: float = 0.40

    # ── Text Similarity Fusion Weights ────────────────────────────
    TFIDF_WEIGHT: float = 0.40
    SEMANTIC_WEIGHT: float = 0.60

    # ── AI Detection ─────────────────────────────────────────────
    GPTZERO_API_KEY: str = ""          # Optional — system works without it
    GPTZERO_LOCAL_WEIGHT: float = 0.50
    GPTZERO_API_WEIGHT: float = 0.50
    MODEL_HMAC_KEY: str = ""           # Key for verifying pickle models

    # ── PDF Retention (days) ─────────────────────────────────────
    PDF_RETENTION_DAYS: int = 90

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
