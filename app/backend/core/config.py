from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "dev"
    APP_NAME: str = "Integra"
    APP_VERSION: str = "1.0.0"
    SECRET_KEY: str = "change-this-to-a-random-secret-key"
    SESSION_COOKIE_NAME: str = "integra_session"
    SESSION_MAX_AGE: int = 604800
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    CHATBOT_API_KEY: str = ""

    DATABASE_URL: str = "postgresql+asyncpg://integra:integra_pass@localhost:5432/integra_db"

    # Observability — see CLAUDE.md "Observability" section.
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "."
    LOG_MAX_BYTES: int = 10_000_000
    LOG_BACKUP_COUNT: int = 5

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = ""
    S3_REGION: str = "us-east-1"

    # JSON completo da credencial de service account do Google Cloud (Drive
    # API habilitada), usado pra importar materiais do Google Docs. O
    # profissional compartilha o doc com o client_email dessa credencial.
    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""


settings = Settings()

_SENSITIVE_FIELDS = {
    "SECRET_KEY",
    "CHATBOT_API_KEY",
    "DATABASE_URL",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
}


def mask_settings(settings_obj: Settings) -> dict:
    """Settings dict safe to write to system.log on startup — used instead
    of logging the Settings object directly, which would leak DATABASE_URL's
    embedded password, the JWT/session secret, API keys, and the Google
    service account private key.
    """
    masked = {}
    for key, value in settings_obj.model_dump().items():
        if key in _SENSITIVE_FIELDS:
            masked[key] = "***" if value else ""
        else:
            masked[key] = value
    return masked
