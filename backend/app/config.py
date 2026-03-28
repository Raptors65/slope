from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: str | None = None
    openrouter_model: str = "google/gemini-3.1-flash-lite-preview"
    # Optional OpenRouter ranking / attribution headers (see OpenRouter docs).
    openrouter_http_referer: str | None = None
    openrouter_app_title: str | None = None

    dashboard_base_url: str = "http://localhost:3000"
    github_pat: str | None = None
    github_webhook_secret: str | None = None
    # Preferred for backend: output of `auggie token print` after `auggie login`
    augment_session_auth: str | None = None
    augment_api_key: str | None = None
    augment_api_url: str | None = None
    # Auggie model id: haiku4.5 | sonnet4.5 | sonnet4 | gpt5 (see auggie_sdk.agent.ModelType).
    augment_model: str = "haiku4.5"
    augment_timeout_seconds: int = 180
    augment_max_cli_turns: int = 8
    augment_clone_timeout_seconds: int = 180

    # Comma-separated origins, e.g. "http://localhost:3000,http://127.0.0.1:3000"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
