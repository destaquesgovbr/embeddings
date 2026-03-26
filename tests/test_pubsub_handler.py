"""
Unit tests for the Pub/Sub /process endpoint and handler.

Tests the event-driven embedding pipeline: receive Pub/Sub push,
fetch from PG, generate embedding locally, update PG, publish event.
"""

import base64
import json
from unittest.mock import patch

import pytest

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def pubsub_envelope():
    data = {"unique_id": "mec-2026-01-01-noticia-1", "enriched_at": "2026-01-01T12:00:00Z"}
    return {
        "message": {
            "data": base64.b64encode(json.dumps(data).encode()).decode(),
            "attributes": {"trace_id": "abc-123", "event_version": "1.0"},
            "messageId": "msg-001",
        },
        "subscription": "projects/test/subscriptions/dgb.news.enriched--embeddings",
    }


@pytest.fixture
def sample_article():
    return {
        "id": 42,
        "title": "Governo anuncia reforma tributária",
        "summary": "Proposta simplifica o sistema tributário brasileiro.",
        "content": "O governo federal anunciou hoje uma nova proposta.",
        "has_embedding": False,
    }


# =============================================================================
# POST /process endpoint tests
# =============================================================================


class TestProcessEndpoint:

    @patch("src.embeddings_api.main.process_article")
    def test_valid_message_returns_200(self, mock_process, client, pubsub_envelope):
        mock_process.return_value = {"status": "embedded", "dimension": 768}
        resp = client.post("/process", json=pubsub_envelope)
        assert resp.status_code == 200
        mock_process.assert_called_once_with("mec-2026-01-01-noticia-1")

    def test_missing_data_returns_400(self, client):
        resp = client.post("/process", json={"message": {}})
        assert resp.status_code == 400

    def test_missing_unique_id_returns_400(self, client):
        data = base64.b64encode(json.dumps({"enriched_at": "2026-01-01"}).encode()).decode()
        resp = client.post("/process", json={"message": {"data": data}})
        assert resp.status_code == 400

    @patch("src.embeddings_api.pubsub_handler.process_article", side_effect=Exception("DB error"))
    def test_error_still_acks(self, mock_process, client, pubsub_envelope):
        resp = client.post("/process", json=pubsub_envelope)
        assert resp.status_code == 200

    def test_no_auth_required(self, client, pubsub_envelope):
        """POST /process does not require X-API-Key (OIDC via Cloud Run IAM)."""
        with patch("src.embeddings_api.pubsub_handler.process_article") as mock:
            mock.return_value = {"status": "embedded"}
            resp = client.post("/process", json=pubsub_envelope)
            assert resp.status_code == 200


# =============================================================================
# Handler: process_article
# =============================================================================


class TestProcessArticle:

    @patch("src.embeddings_api.pubsub_handler.publish_embedded_event")
    @patch("src.embeddings_api.pubsub_handler.update_embedding")
    @patch("src.embeddings_api.pubsub_handler.fetch_article")
    def test_full_pipeline(self, mock_fetch, mock_update, mock_publish, sample_article):
        from src.embeddings_api.pubsub_handler import process_article

        mock_fetch.return_value = sample_article

        result = process_article("mec-2026-01-01-noticia-1")

        assert result["status"] == "embedded"
        assert result["dimension"] == 768
        mock_update.assert_called_once()
        # Verify embedding is a list of 768 floats
        call_args = mock_update.call_args[0]
        assert call_args[0] == 42  # news_id
        assert len(call_args[1]) == 768  # embedding dim
        mock_publish.assert_called_once_with("mec-2026-01-01-noticia-1", 768)

    @patch("src.embeddings_api.pubsub_handler.fetch_article", return_value=None)
    def test_not_found(self, mock_fetch):
        from src.embeddings_api.pubsub_handler import process_article

        result = process_article("nonexistent")
        assert result["status"] == "not_found"

    @patch("src.embeddings_api.pubsub_handler.fetch_article")
    def test_skips_already_embedded(self, mock_fetch):
        from src.embeddings_api.pubsub_handler import process_article

        mock_fetch.return_value = {
            "id": 42, "title": "Test", "summary": None,
            "content": "Test", "has_embedding": True,
        }

        result = process_article("test-1")
        assert result["status"] == "skipped"
        assert result["reason"] == "already_embedded"

    @patch("src.embeddings_api.pubsub_handler.update_embedding", side_effect=Exception("DB error"))
    @patch("src.embeddings_api.pubsub_handler.fetch_article")
    def test_db_error_propagates(self, mock_fetch, mock_update, sample_article):
        from src.embeddings_api.pubsub_handler import process_article

        mock_fetch.return_value = sample_article

        with pytest.raises(Exception, match="DB error"):
            process_article("test-1")


# =============================================================================
# Handler: publish_embedded_event
# =============================================================================


class TestPublishEmbeddedEvent:

    @patch.dict("os.environ", {"PUBSUB_TOPIC_NEWS_EMBEDDED": ""})
    def test_no_publish_without_topic(self):
        from src.embeddings_api.pubsub_handler import publish_embedded_event
        publish_embedded_event("test-1", 768)  # Should not raise

    @patch.dict("os.environ", {"PUBSUB_TOPIC_NEWS_EMBEDDED": "projects/p/topics/t"})
    @patch("google.cloud.pubsub_v1.PublisherClient")
    def test_publishes_correct_data(self, mock_client_class):
        from src.embeddings_api.pubsub_handler import publish_embedded_event

        mock_client = mock_client_class.return_value
        publish_embedded_event("test-1", 768)

        mock_client.publish.assert_called_once()
        call_args = mock_client.publish.call_args
        data = json.loads(call_args[0][1].decode())
        assert data["unique_id"] == "test-1"
        assert data["embedding_dim"] == 768
        assert "embedded_at" in data
