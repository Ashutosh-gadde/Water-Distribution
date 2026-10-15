from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    secret_key: str  # required: no default so a secret is never baked into code
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    min_password_length: int = 12
    cors_origins: str = "http://localhost:5173"


settings = Settings()
