def __getattr__(name):
    if name == "EmbeddingGenerator":
        from .generator import EmbeddingGenerator
        return EmbeddingGenerator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["EmbeddingGenerator"]
