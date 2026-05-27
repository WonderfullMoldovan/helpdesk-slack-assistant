"""
Configurazione dell'applicazione caricata da variabili d'ambiente.

Utilizza Pydantic impostazione per fornire una configurazione validata e con tipizzazione sicura.
Tutti le impostazione vengono caricate una sola volta all'avvioo; la mancanza di valori obligatori
causa un errore immediato dell'applicazione anziche un arresto anomalo successivo.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Impostazione dell'aplicazzione caricato da variabili d'ambiente e file .env
    ordine di letture(la lettura successiva ha la precedenza)

    1.env file
    2.variabili d'ambiente reai

    tutti campi sono obbligatori, a meno che non venga specificato un valore predefinito.
    La mancanza di campi obbligatori causa un VVValidationError all'avvio
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding = "utf-8",
        case_sensitive= False,
        extra ="ignore"
    )

    # ----------------------------
    # Application
    # ----------------------------

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING","ERROR"] = "INFO"

    # ----------------------------
    # Database (PostgreSQL)
    # ----------------------------
    postgres_dsn: str = Field(
        ...,
        description="Full Postresql connection string(asyncpg format)",
    )

    @field_validator("postgres_dsn")
    @classmethod
    def validate_postgres_dsn(cls, v:str) -> str:
        """Ensure DSN uses asyncpg driver (not sync)"""
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "POSTGRES_DSN must start with 'postgresql+asyncpg://' "
                "(async driver required)"
            )
        return v
    # ----------------------------
    # AzureOpenAI
    # ----------------------------
    azure_openai_endpoint:str = Field(
        ...,
        description="Azure OpenAI endpoint URL (e.g. https://my-resource.openai.azure.com/)",
    )

    # Separate API keys for chat and embedding deployments
    azure_openai_api_key: SecretStr = Field(
        ...,
        description="Azure OpenAI API key for chat completions deployment",
    )

    azure_openai_embedding_api_key: SecretStr = Field(
        ...,
        description="Azure OpenAI API key for embedding deployment",
    )

    # Api version - chat needs recent version
    azure_openai_api_version_chat: str = "2025-04-01-preview"
    azure_openai_api_version_embedding: str = "2023-05-15"

    #deployment names
    azure_openai_deployment_chat: str = "gpt-5.4"
    azure_openai_deployment_embedding: str = "text-embedding-3-large"

    # Embedding dimensions — text-embedding-3-large native = 3072,
    # but we truncate to 1536 to match our pgvector Vector(1536) column.
    # This is supported by OpenAI's dimensions parameter without retraining.
    azure_openai_embedding_dimensions: int = Field(
        default=1536,
        ge=256,
        le=3072,
        description="Embedding output dimensions (1536 matches pgvector column)",
    )

    # Reasoning effort for gpt-5.4 — controls latency vs quality trade-off
    # Options: "low", "medium", "high"
    azure_openai_reasoning_effort: Literal["low", "medium", "high"] = "medium"

    # ----------------------------
    # Redis
    # ----------------------------
    redis_url:str = Field(
        ...,
        description="Redis connection URL",
    )

    # ----------------------------
    # Slack
    # ----------------------------
    slack_bot_token:SecretStr = Field(
        ...,
        description="Slack bot token(xoxb-...)",
    )

    slack_signing_secret: SecretStr = Field(
        ...,
        description="Slack signing secret for webhook verification(HMAC-SHA256)",
    )
    slack_app_token: SecretStr | None = Field(
        default=None,
        description="Slack app-level token (xapp-...), only needed for Socket Mode"
    )

    # ----------------------------
    # Langfuse (observability)
    # ----------------------------
    langfuse_public_key: SecretStr = Field(
        ...,
        description="Langfuse public key",
    )
    langfuse_secret_key: SecretStr = Field(
        ...,
        description= "Langfuse secret key",
    )
    langfuse_host: str = "https://cloud.langfuse.com"
    # ----------------------------
    # Agent behavior
    # ----------------------------
    supervisor_confidence_threshold:float = Field(
        default = 0.7,
        ge= 0.0,
        le = 1.0,
        description="Confidence threshold below which Supervisor escalates to human",
    )
    max_graph_steps: int = Field(
        default=15,
        ge=1,
        le=100,
        description="Maximum number of graph transitions per user message(loop protection)",
    )

    reminder_interval_hours:int = Field(
        default=4,
        ge=1,
        description="Hours between escalation reminders",
    )
    max_reminders_per_escalation:int = Field(
        default=2,
        ge=1,
        le=10,
        description="Maximum number of reminders before fallback",
    )
    # ----------------------------
    # Computed properties
    # ----------------------------

    @property
    def is_production(self)  -> bool:
        """True if running in production environment."""
        return self.app_env == "production"
    @property
    def is_development(self) -> bool:
        """True if running in development emvironment."""
        return self.app_env == "development"

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns the singleton Settings instance.

    Cached via lru_cache so we only parse .env / environment once.
    Use this function (or FastAPI Depends(get_settings)) for access.
    """
    return Settings()

settings = get_settings()
