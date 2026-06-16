# Embeddings API

FastAPI service for generating text embeddings using ML models.

## Overview

This service provides a simple HTTP API to generate text embeddings using the **BAAI/bge-m3** model from sentence-transformers. It's designed to run on Google Cloud Run and be called by the data-platform pipeline.

**Model:** BGE-M3 (multilingual, 1024-dim, 8192 max tokens)  
**Validated:** data-science#1 (chosen over mpnet-768d based on NDCG@10, MAP, MRR metrics)

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
  "model": "BAAI/bge-m3",
  "dimension": 1024,
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
| `MODEL_NAME` | Sentence transformer model | `BAAI/bge-m3` |
| `MODEL_DIMENSION` | Expected embedding dimension | `1024` |
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
