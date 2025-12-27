"""Authentication middleware for the Embeddings API."""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .config import settings

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify the API key from the Authorization header.

    Expects: Authorization: Bearer <api_key>
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    # Extract token from "Bearer <token>" format
    if api_key.startswith("Bearer "):
        api_key = api_key[7:]

    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return api_key
