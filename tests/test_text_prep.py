"""Tests for text preparation for embedding generation."""

from embeddings_client.text_prep import MAX_TEXT_LENGTH, prepare_text_for_embedding


class TestPrepareTextForEmbedding:
    def test_title_and_summary(self):
        result = prepare_text_for_embedding("Titulo", "Resumo da noticia", None)
        assert result == "Titulo Resumo da noticia"

    def test_title_only(self):
        result = prepare_text_for_embedding("Titulo", None, None)
        assert result == "Titulo"

    def test_title_with_empty_summary_falls_back_to_content(self):
        result = prepare_text_for_embedding("Titulo", "", "Conteudo completo")
        assert result == "Titulo Conteudo completo"

    def test_title_with_none_summary_falls_back_to_content(self):
        result = prepare_text_for_embedding("Titulo", None, "Conteudo completo")
        assert result == "Titulo Conteudo completo"

    def test_content_fallback_truncated_to_500_chars(self):
        long_content = "A" * 600
        result = prepare_text_for_embedding("T", None, long_content)
        # Title + space + 500 chars of content
        assert len(result) == 1 + 1 + 500

    def test_whitespace_stripped(self):
        result = prepare_text_for_embedding("  Titulo  ", "  Resumo  ", None)
        assert result == "Titulo Resumo"

    def test_whitespace_only_summary_falls_back_to_content(self):
        result = prepare_text_for_embedding("Titulo", "   ", "Conteudo")
        assert result == "Titulo Conteudo"

    def test_truncation_at_max_length(self):
        long_title = "T" * 1000
        long_summary = "S" * 2000
        result = prepare_text_for_embedding(long_title, long_summary, None)
        assert len(result) <= MAX_TEXT_LENGTH * 4

    def test_empty_title(self):
        result = prepare_text_for_embedding("", "Resumo", None)
        assert result == "Resumo"

    def test_all_empty(self):
        result = prepare_text_for_embedding("", None, None)
        assert result == ""

    def test_summary_preferred_over_content(self):
        result = prepare_text_for_embedding("T", "Resumo", "Conteudo")
        assert "Resumo" in result
        assert "Conteudo" not in result
