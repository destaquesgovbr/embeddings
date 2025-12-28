"""Pytest configuration and fixtures."""

import os
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

# Set test API key before importing app
os.environ["API_KEY"] = "test-api-key"

from src.embeddings_api.embedding_service import embedding_service  # noqa: E402
from src.embeddings_api.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def mock_embedding_service():
    """Mock the embedding service to avoid loading the actual model."""
    # Mock the model loading and generation
    original_model = embedding_service._model

    # Create a mock model
    mock_model = Mock()

    # Mock encode to return embeddings based on input length
    def mock_encode(texts, **kwargs):
        """Return mock embeddings matching the number of input texts."""
        import numpy as np
        return np.array([[0.1] * 768 for _ in texts])

    mock_model.encode = mock_encode
    mock_model.get_sentence_embedding_dimension.return_value = 768

    # Replace the model
    embedding_service._model = mock_model

    yield

    # Restore original state
    embedding_service._model = original_model


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authorization headers with test API key."""
    return {"X-API-Key": "test-api-key"}
