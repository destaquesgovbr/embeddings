# Embeddings API

FastAPI service for generating text embeddings using ML models.

## Overview

This service provides a simple HTTP API to generate text embeddings using the `paraphrase-multilingual-mpnet-base-v2` model from sentence-transformers. It's designed to run on Google Cloud Run and be called by the data-platform pipeline.

## API Endpoints

### POST /generate

Generate embeddings for a list of texts.

**Request:**
```json
{
  "texts": [
    "Governo anuncia novo programa de habitação",
    "Ministério da Saúde lança campanha de vacinação"
  ]
}
```

**Response:**
```json
{
  "embeddings": [
    [0.123, -0.456, ...],
    [0.789, -0.012, ...]
  ],
  "model": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
  "dimension": 768,
  "count": 2
}
```

**Authentication:** Requires `Authorization: Bearer <api_key>` header.

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

## Development

### Setup

```bash
# Install dependencies
poetry install

# Run locally
poetry run uvicorn src.embeddings_api.main:app --reload

# Run tests
poetry run pytest -v
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | API key for authentication | `dev-api-key` |
| `MODEL_NAME` | Sentence transformer model | `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` |
| `PORT` | Server port | `8080` |

## Deployment

The service is automatically deployed to Cloud Run when pushing to the `main` branch.

### Manual deployment

```bash
# Build and push image
docker build -t southamerica-east1-docker.pkg.dev/inspire-7-finep/destaquesgovbr-embeddings-api/embeddings-api:latest .
docker push southamerica-east1-docker.pkg.dev/inspire-7-finep/destaquesgovbr-embeddings-api/embeddings-api:latest

# Deploy to Cloud Run
gcloud run deploy destaquesgovbr-embeddings-api \
  --image southamerica-east1-docker.pkg.dev/inspire-7-finep/destaquesgovbr-embeddings-api/embeddings-api:latest \
  --region southamerica-east1 \
  --platform managed
```
