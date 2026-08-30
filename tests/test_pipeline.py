"""
tests/test_pipeline.py — RAGPipeline ve RAGResponse Testleri
=============================================================
Model indirmesi gerektirmez. RAGResponse dataclass'ı doğrudan,
Retriever ve Pipeline davranışı mock ile test edilir.

Çalıştır:
  .\\venv\\Scripts\\python -m pytest tests/test_pipeline.py -v
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag.pipeline import RAGResponse, RAGPipeline
from rag.retriever import Retriever


class TestRAGResponse(unittest.TestCase):
    """RAGResponse dataclass'ı için testler."""

    def test_rag_response_default_fields(self):
        """RAGResponse varsayılan field değerleri doğru olmalı."""
        response = RAGResponse(answer="Test cevabı")
        self.assertEqual(response.answer, "Test cevabı")
        self.assertEqual(response.sources, [])
        self.assertEqual(response.chunks_used, 0)
        self.assertEqual(response.top_chunks, [])
        self.assertEqual(response.retrieval_query, "")
        self.assertEqual(response.latency_sec, 0.0)
        self.assertIsNone(response.error)

    def test_rag_response_has_error_false(self):
        """Error None iken has_error False dönmeli."""
        response = RAGResponse(answer="Cevap")
        self.assertFalse(response.has_error)

    def test_rag_response_has_error_true(self):
        """Error set edilmişken has_error True dönmeli."""
        response = RAGResponse(answer="", error="Bir hata oluştu")
        self.assertTrue(response.has_error)

    def test_rag_response_unique_sources_dedup(self):
        """unique_sources tekrarlı kaynakları temizlemeli."""
        response = RAGResponse(
            answer="Cevap",
            sources=["doc.txt", "other.txt", "doc.txt", "doc.txt"],
        )
        unique = response.unique_sources
        self.assertEqual(len(unique), 2)
        self.assertIn("doc.txt", unique)
        self.assertIn("other.txt", unique)

    def test_rag_response_unique_sources_sorted(self):
        """unique_sources alfabetik sıralı dönmeli."""
        response = RAGResponse(
            answer="Cevap",
            sources=["c_doc.txt", "a_doc.txt", "b_doc.txt"],
        )
        unique = response.unique_sources
        self.assertEqual(unique, sorted(unique))

    def test_rag_response_unique_sources_empty(self):
        """Kaynak yoksa boş liste dönmeli."""
        response = RAGResponse(answer="Cevap", sources=[])
        self.assertEqual(response.unique_sources, [])

    def test_rag_response_chunks_used_tracking(self):
        """chunks_used doğru sayılmalı."""
        response = RAGResponse(answer="Cevap", chunks_used=5)
        self.assertEqual(response.chunks_used, 5)

    def test_rag_response_error_string(self):
        """Error field bir string olabilmeli."""
        error_msg = "empty_database"
        response = RAGResponse(answer="", error=error_msg)
        self.assertEqual(response.error, error_msg)


class TestRetrieverWithMockEmbedder(unittest.TestCase):
    """Retriever sınıfını mock embedder ile test eder."""

    def _make_embedder(self, vector=None):
        if vector is None:
            vector = [0.1] * 384
        mock = MagicMock()
        mock.embed.return_value = vector
        return mock

    def test_retriever_init(self):
        """Retriever doğru şekilde başlatılmalı."""
        embedder = self._make_embedder()
        retriever = Retriever(embedder)
        self.assertIsNotNone(retriever)

    def test_retriever_empty_query_raises(self):
        """Boş sorgu ValueError fırlatmalı."""
        embedder = self._make_embedder()
        retriever = Retriever(embedder)
        with patch("rag.retriever.get_all_chunks", return_value=[]):
            with self.assertRaises(ValueError):
                retriever.get_top_chunks("")

    def test_retriever_whitespace_query_raises(self):
        """Sadece boşluk içeren sorgu ValueError fırlatmalı."""
        embedder = self._make_embedder()
        retriever = Retriever(embedder)
        with patch("rag.retriever.get_all_chunks", return_value=[]):
            with self.assertRaises(ValueError):
                retriever.get_top_chunks("   ")

    def test_retriever_empty_db_returns_empty(self):
        """Veritabanı boşsa boş liste dönmeli."""
        embedder = self._make_embedder()
        retriever = Retriever(embedder)
        with patch("rag.retriever.get_all_chunks", return_value=[]):
            result = retriever.get_top_chunks("Python nedir?")
        self.assertEqual(result, [])

    def test_retriever_returns_top_k(self):
        """get_top_chunks en fazla top_k kadar chunk dönmeli."""
        embedder = self._make_embedder([1.0] + [0.0] * 383)

        # 10 tane sahte chunk oluştur
        fake_chunks = [
            {
                "id": i,
                "source_name": f"doc_{i}.txt",
                "chunk_index": 0,
                "content": f"İçerik {i}. Bu oldukça uzun bir içerik metnidir.",
                "embedding": [1.0] + [0.0] * 383,  # Mükemmel eşleşme
            }
            for i in range(10)
        ]

        with patch("rag.retriever.get_all_chunks", return_value=fake_chunks):
            result = retriever = Retriever(embedder)
            chunks = retriever.get_top_chunks("test sorgusu", top_k=3)

        # En fazla 3 chunk dönmeli
        self.assertLessEqual(len(chunks), 3)

    def test_retriever_score_threshold_filters(self):
        """SCORE_THRESHOLD altındaki chunk'lar filtrelenmeli."""
        # Tamamen alakasız vektörler (dik açı → skor ~0)
        embedder = self._make_embedder([1.0, 0.0, 0.0] + [0.0] * 381)

        fake_chunks = [
            {
                "id": 1,
                "source_name": "unrelated.txt",
                "chunk_index": 0,
                "content": "Tamamen alakasız bir içerik metni.",
                "embedding": [0.0, 1.0, 0.0] + [0.0] * 381,  # Dik açı
            }
        ]

        with patch("rag.retriever.get_all_chunks", return_value=fake_chunks):
            with patch("rag.retriever.SCORE_THRESHOLD", 0.8):  # Çok yüksek eşik
                retriever = Retriever(embedder)
                result = retriever.get_top_chunks("farklı sorgu")

        self.assertEqual(result, [])

    def test_retriever_chunk_has_score_fields(self):
        """Döndürülen chunk'lar score, dense_score, lexical_score alanlarına sahip olmalı."""
        embedder = self._make_embedder([1.0] + [0.0] * 383)
        fake_chunks = [
            {
                "id": 1,
                "source_name": "test.txt",
                "chunk_index": 0,
                "content": "Test içeriği burada yer almaktadır.",
                "embedding": [1.0] + [0.0] * 383,
            }
        ]

        with patch("rag.retriever.get_all_chunks", return_value=fake_chunks):
            with patch("rag.retriever.SCORE_THRESHOLD", 0.0):
                retriever = Retriever(embedder)
                chunks = retriever.get_top_chunks("test")

        if chunks:
            chunk = chunks[0]
            self.assertIn("score", chunk)
            self.assertIn("dense_score", chunk)
            self.assertIn("lexical_score", chunk)


class TestRAGPipelineMock(unittest.TestCase):
    """RAGPipeline'ı tamamen mock edilerek test eder."""

    def _make_pipeline_with_mocks(self):
        """Gerçek model yüklemeden çalışan sahte pipeline döner."""
        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline._embedder = MagicMock()
        pipeline._embedder.embed.return_value = [0.5] * 384
        pipeline._generator = MagicMock()
        pipeline._generator.rewrite_query.side_effect = lambda q, h: q
        pipeline._generator.generate.return_value = "Bu bir test cevabıdır."
        pipeline._retriever = MagicMock()
        pipeline._is_ready = True
        return pipeline

    def test_pipeline_ask_empty_question_raises(self):
        """Boş soru ValueError fırlatmalı."""
        pipeline = self._make_pipeline_with_mocks()
        with self.assertRaises(ValueError):
            pipeline.ask("")

    def test_pipeline_ask_whitespace_raises(self):
        """Sadece boşluk içeren soru ValueError fırlatmalı."""
        pipeline = self._make_pipeline_with_mocks()
        with self.assertRaises(ValueError):
            pipeline.ask("   ")

    def test_pipeline_not_ready_raises(self):
        """Pipeline hazır değilken ask() RuntimeError fırlatmalı."""
        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline._is_ready = False
        with self.assertRaises(RuntimeError):
            pipeline.ask("Soru?")

    def test_pipeline_returns_rag_response(self):
        """ask() her zaman RAGResponse döndürmeli."""
        pipeline = self._make_pipeline_with_mocks()

        mock_chunks = [
            {
                "id": 1,
                "source_name": "test.txt",
                "chunk_index": 0,
                "content": "İçerik.",
                "score": 0.9,
                "dense_score": 0.85,
                "lexical_score": 0.5,
            }
        ]
        pipeline._retriever.get_top_chunks.return_value = mock_chunks
        pipeline._retriever.format_context.return_value = '<belge kaynak="test.txt">\nİçerik.\n</belge>'

        response = pipeline.ask("Test sorusu?")
        self.assertIsInstance(response, RAGResponse)

    def test_pipeline_empty_retrieval_returns_no_error(self):
        """Retrieval sonucu boşsa hata yokken anlamlı cevap dönmeli."""
        pipeline = self._make_pipeline_with_mocks()
        pipeline._retriever.get_top_chunks.return_value = []

        response = pipeline.ask("Bilgi tabanında olmayan bir soru?")
        self.assertIsInstance(response, RAGResponse)
        self.assertFalse(response.has_error)

    def test_pipeline_sources_from_chunks(self):
        """Pipeline, chunk'lardan kaynak adlarını doğru çıkarmalı."""
        pipeline = self._make_pipeline_with_mocks()

        mock_chunks = [
            {"id": 1, "source_name": "python.txt", "chunk_index": 0,
             "content": "İçerik.", "score": 0.9, "dense_score": 0.9, "lexical_score": 0.5},
            {"id": 2, "source_name": "rag.txt", "chunk_index": 0,
             "content": "İçerik 2.", "score": 0.8, "dense_score": 0.8, "lexical_score": 0.4},
        ]
        pipeline._retriever.get_top_chunks.return_value = mock_chunks
        pipeline._retriever.format_context.return_value = "bağlam"

        response = pipeline.ask("Soru?")
        self.assertIn("python.txt", response.sources)
        self.assertIn("rag.txt", response.sources)

    def test_pipeline_generator_error_handled(self):
        """Generator hata fırlatırsa RAGResponse error field'ı dolu dönmeli."""
        pipeline = self._make_pipeline_with_mocks()

        mock_chunks = [
            {"id": 1, "source_name": "test.txt", "chunk_index": 0,
             "content": "İçerik.", "score": 0.9, "dense_score": 0.9, "lexical_score": 0.5},
        ]
        pipeline._retriever.get_top_chunks.return_value = mock_chunks
        pipeline._retriever.format_context.return_value = "bağlam"
        pipeline._generator.generate.side_effect = RuntimeError("Model çöktü")

        response = pipeline.ask("Hata tetikleyen soru?")
        self.assertIsInstance(response, RAGResponse)
        self.assertTrue(response.has_error)


if __name__ == "__main__":
    unittest.main()
