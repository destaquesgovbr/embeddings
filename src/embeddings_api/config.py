"""Configuration settings for the Embeddings API."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API authentication
    api_key: str = "dev-api-key"

    # Documentation
    docs_enabled: bool = True

    # Model configuration
    # BGE-M3: multilingual, 1024-dim, 8192 max tokens
    # Validated in data-science#1, chosen over mpnet-768d
    model_name: str = "BAAI/bge-m3"
    model_dimension: int = 1024

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8080

    # Batch processing
    max_batch_size: int = 100

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()
