FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files and README (needed by Poetry)
COPY pyproject.toml poetry.lock README.md ./

# Install dependencies (no dev deps, no virtualenv)
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Copy application code
COPY src/ ./src/

# Pre-download ML model (cached in image layer ~1.2GB)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')"

# Environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Run the application
CMD ["uvicorn", "src.embeddings_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
