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

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = ""
    S3_REGION: str = "us-east-1"


settings = Settings()
