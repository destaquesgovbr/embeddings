"""
Pub/Sub push handler for event-driven embedding generation.

Receives dgb.news.enriched events, generates embeddings using the
local model (no HTTP hop), updates PostgreSQL, and publishes
dgb.news.embedded events.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

import psycopg2

from embeddings_client.text_prep import prepare_text_for_embedding

from .embedding_service import embedding_service

logger = logging.getLogger(__name__)


def _get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return url


def fetch_article(unique_id: str) -> dict | None:
    """Fetch article fields needed for embedding generation."""
    conn = psycopg2.connect(_get_database_url())
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, summary, content, content_embedding FROM news WHERE unique_id = %s",
                (unique_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return {
                "id": row[0],
                "title": row[1],
                "summary": row[2],
                "content": row[3],
                "has_embedding": row[4] is not None,
            }
    finally:
        conn.close()


def update_embedding(news_id: int, embedding: list[float]) -> None:
    """Update news record with generated embedding."""
    conn = psycopg2.connect(_get_database_url())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE news
                SET content_embedding = %s::vector,
                    embedding_generated_at = %s
                WHERE id = %s
                """,
                (embedding, datetime.now(timezone.utc), news_id),
            )
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def publish_embedded_event(unique_id: str, embedding_dim: int) -> None:
    """Publish dgb.news.embedded event to Pub/Sub."""
    topic = os.environ.get("PUBSUB_TOPIC_NEWS_EMBEDDED")
    if not topic:
        return

    try:
        from google.cloud import pubsub_v1

        client = pubsub_v1.PublisherClient()
        message = {
            "unique_id": unique_id,
            "embedded_at": datetime.now(timezone.utc).isoformat(),
            "embedding_dim": embedding_dim,
        }
        client.publish(
            topic,
            json.dumps(message).encode("utf-8"),
            trace_id=str(uuid.uuid4()),
            event_version="1.0",
        )
        logger.info(f"Published dgb.news.embedded for {unique_id}")
    except Exception as e:
        logger.warning(f"Failed to publish embedded event for {unique_id}: {e}")


def process_article(unique_id: str) -> dict:
    """
    Full embedding pipeline for a single article.

    Uses the local model (no HTTP call to /generate).
    """
    article = fetch_article(unique_id)
    if article is None:
        logger.warning(f"Article not found: {unique_id}")
        return {"status": "not_found"}

    # Idempotency
    if article["has_embedding"]:
        logger.info(f"Already has embedding: {unique_id}")
        return {"status": "skipped", "reason": "already_embedded"}

    if not embedding_service.is_loaded:
        logger.error("Model not loaded")
        return {"status": "error", "reason": "model_not_loaded"}

    # Prepare text
    text = prepare_text_for_embedding(
        title=article["title"] or "",
        summary=article["summary"],
        content=article["content"],
    )

    # Generate embedding directly (no HTTP hop)
    embeddings = embedding_service.generate([text])
    embedding = embeddings[0]

    # Update PostgreSQL
    update_embedding(article["id"], embedding)
    logger.info(f"Embedding stored for {unique_id} (dim={len(embedding)})")

    # Publish event
    publish_embedded_event(unique_id, len(embedding))

    return {"status": "embedded", "dimension": len(embedding)}
