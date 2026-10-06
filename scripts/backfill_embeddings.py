#!/usr/bin/env python3
"""
Backfill embeddings for all news articles that don't have one yet.

Connects to PostgreSQL, finds articles with NULL content_embedding,
generates embeddings via the remote Embeddings API (Cloud Run),
and updates the database in batches. Supports parallel workers with
retry and exponential backoff.

Usage:
    # Dry run — just count missing embeddings
    python scripts/backfill_embeddings.py --dry-run

    # Run with 6 parallel workers
    python scripts/backfill_embeddings.py --workers 6

    # Custom batch size and limit
    python scripts/backfill_embeddings.py --batch-size 100 --limit 1000

    # Filter by date range
    python scripts/backfill_embeddings.py --start-date 2024-01-01 --end-date 2024-12-31

Environment variables:
    DATABASE_URL          — PostgreSQL connection string (required)
    EMBEDDINGS_API_URL    — Embeddings API base URL (required)
    EMBEDDINGS_API_KEY    — API key for X-API-Key header (required)
"""

import argparse
import json
import logging
import os
import sys
import time
import threading
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from threading import Lock

import psycopg2
from psycopg2.extras import execute_values

# Add src/ to path so we can import text_prep
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from embeddings_client.text_prep import prepare_text_for_embedding

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

API_MAX_BATCH = 100
MAX_RETRIES = 5

# Shared counters
stats_lock = Lock()
total_processed = 0
total_errors = 0


def get_env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        raise RuntimeError(f"{name} not set")
    return val


_REQUIRE_SUMMARY_SQL = " AND summary IS NOT NULL"


def count_missing(conn, start_date, end_date, require_summary: bool = False) -> int:
    query = "SELECT COUNT(*) FROM news WHERE content_embedding IS NULL"
    if require_summary:
        query += _REQUIRE_SUMMARY_SQL
    params = []
    if start_date:
        query += " AND published_at >= %s"
        params.append(start_date)
    if end_date:
        query += " AND published_at < %s"
        params.append(end_date)
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchone()[0]


def fetch_batch_by_ids(conn, ids, require_summary: bool = False) -> list:
    query = """
        SELECT id, unique_id, title, summary, content
        FROM news
        WHERE id = ANY(%s) AND content_embedding IS NULL
    """
    if require_summary:
        query += _REQUIRE_SUMMARY_SQL
    with conn.cursor() as cur:
        cur.execute(query, (ids,))
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def fetch_ids_missing_embeddings(
    conn, total_needed, start_date, end_date, require_summary: bool = False
) -> list:
    query = "SELECT id FROM news WHERE content_embedding IS NULL"
    if require_summary:
        query += _REQUIRE_SUMMARY_SQL
    params = []
    if start_date:
        query += " AND published_at >= %s"
        params.append(start_date)
    if end_date:
        query += " AND published_at < %s"
        params.append(end_date)
    query += " ORDER BY published_at DESC"
    if total_needed:
        query += " LIMIT %s"
        params.append(total_needed)
    with conn.cursor() as cur:
        cur.execute(query, params)
        return [row[0] for row in cur.fetchall()]


def generate_embeddings_via_api(api_url: str, api_key: str, texts: list, worker_id: int = 0) -> list:
    """Call API with retry and exponential backoff."""
    body = json.dumps({"texts": texts}).encode()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                f"{api_url}/generate",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": api_key,
                },
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.load(resp)
            return data["embeddings"]
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
            wait = min(2 ** attempt, 60)  # 2, 4, 8, 16, 60
            logger.warning(f"[W{worker_id}] Attempt {attempt}/{MAX_RETRIES} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)

    raise RuntimeError(f"API failed after {MAX_RETRIES} retries")


def update_embeddings(conn, updates) -> int:
    query = """
        UPDATE news AS n
        SET content_embedding = v.embedding::vector,
            embedding_generated_at = v.generated_at
        FROM (VALUES %s) AS v(embedding, generated_at, id)
        WHERE n.id = v.id
    """
    with conn.cursor() as cur:
        execute_values(cur, query, updates, template="(%s::vector, %s, %s)")
    conn.commit()
    return len(updates)


def process_chunk(worker_id, ids, batch_size, db_url, api_url, api_key, require_summary=False):
    """Process a chunk of article IDs with its own DB connection."""
    global total_processed, total_errors

    conn = psycopg2.connect(db_url)
    worker_processed = 0

    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i : i + batch_size]

        articles = fetch_batch_by_ids(conn, batch_ids, require_summary)
        if not articles:
            continue

        texts = []
        valid_articles = []
        for article in articles:
            text = prepare_text_for_embedding(
                title=article["title"] or "",
                summary=article["summary"],
                content=article["content"],
            )
            if text.strip():
                texts.append(text)
                valid_articles.append(article)

        if not texts:
            continue

        try:
            embeddings = generate_embeddings_via_api(api_url, api_key, texts, worker_id)
        except RuntimeError as e:
            logger.error(f"[W{worker_id}] Gave up on batch: {e}")
            with stats_lock:
                total_errors += len(texts)
            continue

        now = datetime.now(timezone.utc)
        updates = [
            (emb, now, article["id"])
            for emb, article in zip(embeddings, valid_articles)
        ]

        updated = update_embeddings(conn, updates)
        worker_processed += updated

        with stats_lock:
            total_processed += updated

    conn.close()
    return worker_processed


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Backfill embeddings for news articles missing them."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--start-date", type=str, default=None)
    parser.add_argument("--end-date", type=str, default=None)
    parser.add_argument(
        "--require-summary",
        action="store_true",
        help="só artigos com summary (o texto do embedding é título + resumo; "
        "evita congelar embedding sem resumo de artigo que ainda vai ganhá-lo)",
    )
    return parser.parse_args(argv)


def main():
    global total_processed, total_errors

    args = parse_args()

    if args.batch_size > API_MAX_BATCH:
        args.batch_size = API_MAX_BATCH

    db_url = get_env("DATABASE_URL")
    conn = psycopg2.connect(db_url)

    missing = count_missing(conn, args.start_date, args.end_date, args.require_summary)
    target = min(missing, args.limit) if args.limit else missing
    logger.info(
        f"Articles without embeddings: {missing}"
        + (" (com summary)" if args.require_summary else "")
    )
    logger.info(f"Target: {target}")

    if args.dry_run or missing == 0:
        conn.close()
        return

    api_url = get_env("EMBEDDINGS_API_URL").rstrip("/")
    api_key = get_env("EMBEDDINGS_API_KEY")

    # Verify API health
    req = urllib.request.Request(f"{api_url}/health")
    with urllib.request.urlopen(req, timeout=10) as resp:
        health = json.load(resp)
    if not health.get("model_loaded"):
        raise RuntimeError("Embeddings API model not loaded")
    logger.info(f"API healthy at {api_url}")

    # Fetch all IDs upfront
    logger.info(f"Fetching IDs...")
    all_ids = fetch_ids_missing_embeddings(
        conn, target, args.start_date, args.end_date, args.require_summary
    )
    conn.close()
    target = len(all_ids)

    n_workers = max(1, args.workers)
    chunk_size = len(all_ids) // n_workers
    chunks = []
    for i in range(n_workers):
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size if i < n_workers - 1 else len(all_ids)
        chunks.append(all_ids[start_idx:end_idx])

    logger.info(
        f"Starting {n_workers} workers, ~{chunk_size} articles each, "
        f"batch_size={args.batch_size}"
    )

    start_time = time.time()

    # Progress reporter
    def report_progress():
        while total_processed < target:
            time.sleep(15)
            with stats_lock:
                proc = total_processed
                errs = total_errors
            elapsed = time.time() - start_time
            rate = proc / elapsed if elapsed > 0 else 0
            remaining = (target - proc) / rate if rate > 0 else 0
            logger.info(
                f"Progress: {proc}/{target} "
                f"({proc * 100 / target:.1f}%) | "
                f"{rate:.1f} art/s | ETA: {remaining / 60:.0f}m | "
                f"errors: {errs}"
            )

    progress_thread = threading.Thread(target=report_progress, daemon=True)
    progress_thread.start()

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = {
            executor.submit(
                process_chunk,
                worker_id=i,
                ids=chunk,
                batch_size=args.batch_size,
                db_url=db_url,
                api_url=api_url,
                api_key=api_key,
                require_summary=args.require_summary,
            ): i
            for i, chunk in enumerate(chunks)
        }

        for future in as_completed(futures):
            wid = futures[future]
            try:
                count = future.result()
                logger.info(f"[W{wid}] Done: {count} articles")
            except Exception as e:
                logger.error(f"[W{wid}] Failed: {e}")

    elapsed = time.time() - start_time
    logger.info(
        f"Done. Processed: {total_processed}, errors: {total_errors}, "
        f"time: {elapsed / 60:.1f}m ({total_processed / elapsed:.1f} art/s)"
    )


if __name__ == "__main__":
    main()
