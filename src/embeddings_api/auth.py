"""Authentication middleware for the Embeddings API."""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .config import settings

# Use X-API-Key header (Authorization is used by Cloud Run IAM)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify the API key from the X-API-Key header."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return api_key
