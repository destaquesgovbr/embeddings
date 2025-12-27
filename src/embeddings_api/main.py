"""FastAPI application for generating text embeddings."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status

from . import __version__
from .auth import verify_api_key
from .embedding_service import embedding_service
from .schemas import ErrorResponse, GenerateRequest, GenerateResponse, HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the ML model on startup."""
    logger.info("Starting Embeddings API...")
    embedding_service.load_model()
    logger.info("Model loaded, API ready")
    yield
    logger.info("Shutting down Embeddings API...")


app = FastAPI(
    title="Embeddings API",
    description="API for generating text embeddings using ML models",
    version=__version__,
    lifespan=lifespan,
)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check endpoint",
)
async def health_check() -> HealthResponse:
    """Check the health status of the API and model."""
    return HealthResponse(
        status="healthy",
        model_loaded=embedding_service.is_loaded,
    )


@app.post(
    "/generate",
    response_model=GenerateResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    tags=["Embeddings"],
    summary="Generate embeddings for texts",
    dependencies=[Depends(verify_api_key)],
)
async def generate_embeddings(request: GenerateRequest) -> GenerateResponse:
    """Generate embeddings for a list of texts.

    Requires authentication via API key in the Authorization header:
    `Authorization: Bearer <api_key>`
    """
    if not embedding_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded",
        )

    try:
        embeddings = embedding_service.generate(request.texts)
        return GenerateResponse(
            embeddings=embeddings,
            model=embedding_service.model_name,
            dimension=embedding_service.dimension,
            count=len(embeddings),
        )
    except Exception as e:
        logger.exception("Error generating embeddings")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


if __name__ == "__main__":
    import uvicorn

    from .config import settings

    uvicorn.run(app, host=settings.host, port=settings.port)
