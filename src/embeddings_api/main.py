"""FastAPI application for generating text embeddings."""

import base64
import json
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status

from . import __version__
from .auth import verify_api_key
from .embedding_service import embedding_service
from .pubsub_handler import process_article
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

    Requires authentication via API key in the X-API-Key header.
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


@app.post(
    "/process",
    tags=["Pub/Sub"],
    summary="Process Pub/Sub push message for embedding generation",
)
async def process_pubsub(request: Request) -> Response:
    """Handle Pub/Sub push message from dgb.news.enriched.

    No API key required — authenticated via Pub/Sub push OIDC token
    verified by Cloud Run IAM.
    """
    try:
        envelope = await request.json()
    except Exception:
        return Response(status_code=400, content="Invalid JSON")

    message = envelope.get("message", {})
    data_b64 = message.get("data")
    if not data_b64:
        return Response(status_code=400, content="No data")

    try:
        payload = json.loads(base64.b64decode(data_b64))
    except Exception:
        return Response(status_code=400, content="Invalid data encoding")

    unique_id = payload.get("unique_id")
    if not unique_id:
        return Response(status_code=400, content="Missing unique_id")

    trace_id = message.get("attributes", {}).get("trace_id", "")
    logger.info(f"Processing embedding for {unique_id} (trace={trace_id})")

    try:
        result = process_article(unique_id)
        logger.info(f"Result for {unique_id}: {result['status']}")
        return Response(status_code=200, content=json.dumps(result))
    except Exception as e:
        logger.error(f"Error processing {unique_id}: {e}", exc_info=True)
        return Response(status_code=200, content=f"ACK (error: {e})")


if __name__ == "__main__":
    import uvicorn

    from .config import settings

    uvicorn.run(app, host=settings.host, port=settings.port)
