"""Testes do scripts/backfill_embeddings.py (seleção do backfill)."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "backfill_embeddings.py"


@pytest.fixture(scope="module")
def backfill():
    spec = importlib.util.spec_from_file_location("backfill_embeddings", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, query, params=None):
        self.queries.append((query, list(params or [])))

    def fetchone(self):
        return self.rows[0]

    def fetchall(self):
        return self.rows


class _Conn:
    def __init__(self, rows):
        self.cur = _Cursor(rows)

    def cursor(self):
        return self.cur


def test_require_summary_filtra_contagem(backfill):
    conn = _Conn([(7,)])
    assert backfill.count_missing(conn, "2026-06-01", "2026-10-06", require_summary=True) == 7
    query, params = conn.cur.queries[0]
    assert "content_embedding IS NULL" in query
    assert "summary IS NOT NULL" in query
    assert params == ["2026-06-01", "2026-10-06"]


def test_require_summary_filtra_ids(backfill):
    conn = _Conn([(1,), (2,)])
    ids = backfill.fetch_ids_missing_embeddings(
        conn, 10, "2026-06-01", "2026-10-06", require_summary=True
    )
    assert ids == [1, 2]
    query, _ = conn.cur.queries[0]
    assert "summary IS NOT NULL" in query
    assert query.index("summary IS NOT NULL") < query.index("ORDER BY")


def test_sem_require_summary_mantem_comportamento(backfill):
    conn = _Conn([(3,)])
    backfill.count_missing(conn, None, None)
    query, params = conn.cur.queries[0]
    assert "summary IS NOT NULL" not in query
    assert params == []


def test_lote_por_ids_respeita_require_summary(backfill):
    conn = _Conn([])
    backfill.fetch_batch_by_ids(conn, [1, 2], require_summary=True)
    query, _ = conn.cur.queries[0]
    assert "summary IS NOT NULL" in query


def test_cli_aceita_require_summary(backfill):
    args = backfill.parse_args(["--require-summary", "--end-date", "2026-10-06"])
    assert args.require_summary is True
    assert backfill.parse_args([]).require_summary is False
