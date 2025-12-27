"""Pydantic schemas for request and response models."""

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Request body for embedding generation."""

    texts: list[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of texts to generate embeddings for (max 100)",
    )


class GenerateResponse(BaseModel):
    """Response body for embedding generation."""

    embeddings: list[list[float]] = Field(
        ...,
        description="List of embedding vectors (768 dimensions each)",
    )
    model: str = Field(
        ...,
        description="Name of the model used to generate embeddings",
    )
    dimension: int = Field(
        ...,
        description="Dimension of the embedding vectors",
    )
    count: int = Field(
        ...,
        description="Number of embeddings generated",
    )


class HealthResponse(BaseModel):
    """Response body for health check."""

    status: str = Field(
        ...,
        description="Health status of the service",
    )
    model_loaded: bool = Field(
        ...,
        description="Whether the ML model is loaded and ready",
    )


class ErrorResponse(BaseModel):
    """Error response body."""

    detail: str = Field(
        ...,
        description="Error message",
    )
