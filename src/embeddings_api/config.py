"""Configuration settings for the Embeddings API."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API authentication
    api_key: str = "dev-api-key"

    # Model configuration
    model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8080

    # Batch processing
    max_batch_size: int = 100

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()
