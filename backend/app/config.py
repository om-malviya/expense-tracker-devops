from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the API.

    Every field can be overridden by an environment variable with the same name in upper
    case (APP_NAME, APP_ENV, LOG_LEVEL, DATABASE_URL, CORS_ORIGINS). I keep the defaults
    safe for local development only: in Docker Compose the values come from the compose
    file, and in Kubernetes the non-sensitive ones come from a ConfigMap while DATABASE_URL
    is injected from a Secret. A `.env` file is honoured for convenience but never committed.
    """

    app_name: str = "Expense Tracker API"
    app_env: str = "local"
    log_level: str = "info"
    # Comma-separated list of browser origins allowed by CORS. A wildcard "*" is deliberately
    # NOT used: it gets flagged by SAST scanners and is unnecessary because in Compose/K8s
    # the browser reaches the API through the frontend nginx proxy (same origin). Only the
    # Vite dev server (5173) and the compose frontend port (3000) are allowed by default.
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    # The password below is a local-only placeholder that matches docker-compose.yml;
    # real deployments always override DATABASE_URL.
    database_url: str = "postgresql+psycopg://expenses:expenses-local-only@localhost:5432/expenses"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
