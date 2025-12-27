# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Install poetry with export plugin
RUN pip install --no-cache-dir poetry poetry-plugin-export

# Copy dependency files
COPY pyproject.toml poetry.lock README.md ./

# Export requirements (without dev dependencies)
RUN poetry export --only main --without-hashes -f requirements.txt -o requirements.txt

# Copy source code for building the package
COPY src/ ./src/

# Build the package wheel
RUN poetry build -f wheel

# Stage 2: Runtime image
FROM python:3.12-slim

WORKDIR /app

# Install torch CPU-only FIRST (much smaller than CUDA version ~200MB vs ~2GB)
# This must be done before requirements.txt to override the default torch
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies from requirements.txt (exclude torch since we already installed it)
COPY --from=builder /app/requirements.txt .
RUN grep -v "^torch==" requirements.txt > requirements-no-torch.txt \
    && pip install --no-cache-dir -r requirements-no-torch.txt \
    && rm requirements.txt requirements-no-torch.txt

# Install our package
COPY --from=builder /app/dist/*.whl .
RUN pip install --no-cache-dir --no-deps *.whl \
    && rm *.whl

# Pre-download ML model
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')"

# Cleanup: remove unnecessary files to reduce image size
# NOTE: Keep /root/.cache/huggingface - contains the pre-downloaded ML model!
RUN find /usr/local/lib/python3.12 -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.12 -type f -name "*.pyc" -delete 2>/dev/null || true \
    && find /usr/local/lib/python3.12 -type f -name "*.pyo" -delete 2>/dev/null || true \
    && rm -rf /root/.cache/pip \
    && rm -rf /tmp/*

# Environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Run the application
CMD ["uvicorn", "embeddings_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
