"""Embedding generation service using sentence-transformers."""

import logging
from typing import ClassVar

from sentence_transformers import SentenceTransformer

from .config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using sentence-transformers."""

    _instance: ClassVar["EmbeddingService | None"] = None
    _model: SentenceTransformer | None = None

    def __new__(cls) -> "EmbeddingService":
        """Singleton pattern to ensure only one model is loaded."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_model(self) -> None:
        """Load the sentence-transformers model."""
        if self._model is None:
            logger.info(f"Loading model: {settings.model_name}")
            self._model = SentenceTransformer(settings.model_name)
            logger.info(f"Model loaded. Embedding dimension: {self.dimension}")

    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._model is not None

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        if self._model is None:
            return settings.model_dimension  # Default from config (1024 for BGE-M3)
        return self._model.get_sentence_embedding_dimension()

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return settings.model_name

    def generate(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of texts to generate embeddings for.

        Returns:
            List of embedding vectors.

        Raises:
            RuntimeError: If the model is not loaded.
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        logger.info(f"Generating embeddings for {len(texts)} texts")
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()


# Global singleton instance
embedding_service = EmbeddingService()
