"""Tests for the Embeddings API endpoints."""


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_check_returns_200(self, client):
        """Health check should return 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_returns_status(self, client):
        """Health check should return status field."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_check_returns_model_loaded(self, client):
        """Health check should return model_loaded field."""
        response = client.get("/health")
        data = response.json()
        assert "model_loaded" in data
        assert isinstance(data["model_loaded"], bool)


class TestGenerateEndpoint:
    """Tests for the /generate endpoint."""

    def test_generate_requires_auth(self, client):
        """Generate endpoint should require authentication."""
        response = client.post("/generate", json={"texts": ["test"]})
        assert response.status_code == 401

    def test_generate_with_invalid_api_key(self, client):
        """Generate endpoint should reject invalid API key."""
        headers = {"X-API-Key": "wrong-key"}
        response = client.post("/generate", json={"texts": ["test"]}, headers=headers)
        assert response.status_code == 401

    def test_generate_with_valid_api_key(self, client, auth_headers):
        """Generate endpoint should accept valid API key."""
        response = client.post(
            "/generate",
            json={"texts": ["Teste de embedding"]},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_generate_returns_embeddings(self, client, auth_headers):
        """Generate endpoint should return embeddings."""
        response = client.post(
            "/generate",
            json={"texts": ["Teste de embedding"]},
            headers=auth_headers,
        )
        data = response.json()
        assert "embeddings" in data
        assert len(data["embeddings"]) == 1

    def test_generate_returns_correct_dimension(self, client, auth_headers):
        """Generate endpoint should return 768-dimensional embeddings."""
        response = client.post(
            "/generate",
            json={"texts": ["Teste de embedding"]},
            headers=auth_headers,
        )
        data = response.json()
        assert data["dimension"] == 768
        assert len(data["embeddings"][0]) == 768

    def test_generate_multiple_texts(self, client, auth_headers):
        """Generate endpoint should handle multiple texts."""
        texts = ["Primeiro texto", "Segundo texto", "Terceiro texto"]
        response = client.post("/generate", json={"texts": texts}, headers=auth_headers)
        data = response.json()
        assert data["count"] == 3
        assert len(data["embeddings"]) == 3

    def test_generate_returns_model_name(self, client, auth_headers):
        """Generate endpoint should return model name."""
        response = client.post(
            "/generate",
            json={"texts": ["Teste"]},
            headers=auth_headers,
        )
        data = response.json()
        assert "model" in data
        assert "paraphrase-multilingual" in data["model"]

    def test_generate_empty_texts_fails(self, client, auth_headers):
        """Generate endpoint should reject empty texts list."""
        response = client.post("/generate", json={"texts": []}, headers=auth_headers)
        assert response.status_code == 422

    def test_generate_too_many_texts_fails(self, client, auth_headers):
        """Generate endpoint should reject more than 100 texts."""
        texts = ["text"] * 101
        response = client.post("/generate", json={"texts": texts}, headers=auth_headers)
        assert response.status_code == 422


class TestAuthFormats:
    """Tests for different auth header formats."""

    def test_x_api_key_header(self, client):
        """Should accept X-API-Key header format."""
        headers = {"X-API-Key": "test-api-key"}
        response = client.post("/generate", json={"texts": ["test"]}, headers=headers)
        assert response.status_code == 200

    def test_missing_api_key_header(self, client):
        """Should reject requests without X-API-Key header."""
        response = client.post("/generate", json={"texts": ["test"]})
        assert response.status_code == 401
