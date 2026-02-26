"""
DAG para gerar embeddings de noticias via Embeddings API (Cloud Run).

Executa diariamente apos o pipeline de enrichment.
Processa noticias do dia anterior (logical_date - 1 day).

Pipeline: PostgreSQL → Embeddings API → PostgreSQL (pgvector)
"""

from datetime import datetime, timedelta, timezone
import logging

from airflow.decorators import dag, task
from airflow.hooks.base import BaseHook


@dag(
    dag_id="generate_embeddings",
    description="Gera embeddings de noticias via Embeddings API",
    schedule="0 5 * * *",  # 5 AM UTC (1h apos main-workflow)
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["embeddings", "postgres", "daily"],
    default_args={
        "owner": "embeddings",
        "depends_on_past": False,
        "email_on_failure": False,
        "email_on_retry": False,
        "retries": 3,
        "retry_delay": timedelta(minutes=5),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=30),
    },
)
def generate_embeddings_dag():
    """
    DAG que gera embeddings semanticos para noticias.

    Usa a Embeddings API (Cloud Run) para gerar vetores 768-dim
    e grava de volta no PostgreSQL (pgvector).
    """

    @task
    def generate(logical_date=None) -> dict:
        """
        Task que gera embeddings para noticias do dia anterior.

        Returns:
            dict: Estatisticas da geracao (processed, successful, failed)
        """
        from embeddings_client import EmbeddingGenerator

        # Obter connections do Airflow
        pg_conn = BaseHook.get_connection("postgres_default")
        emb_conn = BaseHook.get_connection("embeddings_api")

        # Data alvo: dia anterior ao logical_date
        if logical_date is None:
            logical_date = datetime.now(timezone.utc)
            logging.info("Execucao manual detectada - usando data atual como logical_date")
        target_date = (logical_date - timedelta(days=1)).strftime("%Y-%m-%d")
        logging.info(f"Gerando embeddings para data: {target_date}")

        # Montar database_url a partir da connection
        database_url = pg_conn.get_uri()

        generator = EmbeddingGenerator(
            database_url=database_url,
            api_url=emb_conn.host,
            api_key=emb_conn.password,
        )

        result = generator.generate_embeddings(
            start_date=target_date,
            end_date=target_date,
        )

        logging.info("=" * 60)
        logging.info("Embedding Generation Concluida")
        logging.info("=" * 60)
        logging.info(f"Data processada: {target_date}")
        logging.info(f"Registros processados: {result['processed']}")
        logging.info(f"Sucesso: {result['successful']}")
        logging.info(f"Falhas: {result['failed']}")
        logging.info("=" * 60)

        return result

    generate()


dag_instance = generate_embeddings_dag()
