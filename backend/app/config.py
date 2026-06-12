from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://kith:kith@localhost:5432/kith"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_fallback_model: str = "gemini-2.0-flash"


settings = Settings()
