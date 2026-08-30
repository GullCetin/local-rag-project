"""
tests/test_retriever.py — Hibrit Arama ve Retrieval Mantığı Testleri (Genişletilmiş)
=====================================================================================
Bu testler model indirmesi gerektirmez, doğrudan hibrit arama,
sözcük puanlama, stopword filtreleme ve bağlam formatlama algoritmalarını doğrular.

Çalıştır:
  .\\venv\\Scripts\\python -m pytest tests/test_retriever.py -v
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag.retriever import calculate_lexical_score, cosine_similarity, Retriever


class TestCosimeSimilarity(unittest.TestCase):

    def test_cosine_similarity_identical_vectors(self):
        """Aynı vektörler 1.0 benzerlik skoru vermeli."""
        v1 = [1.0, 2.0, 3.0]
        v2 = [1.0, 2.0, 3.0]
        self.assertAlmostEqual(cosine_similarity(v1, v2), 1.0, places=4)

    def test_cosine_similarity_orthogonal_vectors(self):
        """Birbirine dik vektörler 0.0 benzerlik skoru vermeli."""
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        self.assertAlmostEqual(cosine_similarity(v1, v2), 0.0, places=4)

    def test_cosine_similarity_zero_vector(self):
        """Sıfır vektörü hata fırlatmadan 0.0 dönmeli."""
        v1 = [0.0, 0.0, 0.0]
        v2 = [1.0, 2.0, 3.0]
        self.assertEqual(cosine_similarity(v1, v2), 0.0)

    def test_cosine_similarity_both_zero_vectors(self):
        """Her iki vektör de sıfır olduğunda 0.0 dönmeli."""
        v1 = [0.0, 0.0]
        v2 = [0.0, 0.0]
        self.assertEqual(cosine_similarity(v1, v2), 0.0)

    def test_cosine_similarity_opposite_vectors(self):
        """Zıt yönlü vektörler negatif skor (-1.0'a yakın) vermeli."""
        v1 = [1.0, 0.0, 0.0]
        v2 = [-1.0, 0.0, 0.0]
        result = cosine_similarity(v1, v2)
        self.assertAlmostEqual(result, -1.0, places=4)

    def test_cosine_similarity_scaled_vectors(self):
        """Skalar ile ölçeklenmiş vektörler aynı yönde → 1.0 vermeli."""
        v1 = [1.0, 2.0, 3.0]
        v2 = [2.0, 4.0, 6.0]  # v1 * 2
        self.assertAlmostEqual(cosine_similarity(v1, v2), 1.0, places=4)

    def test_cosine_similarity_high_dimensional(self):
        """384 boyutlu vektörlerde (gerçek embedding boyutu) hesaplama doğru çalışmalı."""
        import random
        random.seed(42)
        v1 = [random.uniform(-1, 1) for _ in range(384)]
        v2 = list(v1)  # Aynı vektör
        result = cosine_similarity(v1, v2)
        self.assertAlmostEqual(result, 1.0, places=4)

    def test_cosine_similarity_range(self):
        """Cosine similarity -1.0 ile 1.0 arasında olmalı."""
        import random
        random.seed(7)
        v1 = [random.uniform(-1, 1) for _ in range(64)]
        v2 = [random.uniform(-1, 1) for _ in range(64)]
        result = cosine_similarity(v1, v2)
        self.assertGreaterEqual(result, -1.0)
        self.assertLessEqual(result, 1.0)

    def test_cosine_similarity_returns_float(self):
        """Dönüş tipi float olmalı."""
        result = cosine_similarity([1.0, 0.0], [0.5, 0.5])
        self.assertIsInstance(result, float)


class TestLexicalScore(unittest.TestCase):

    def test_lexical_score_source_name_match(self):
        """Dosya adı sorgudaki terimi içeriyorsa yüksek puan vermeli."""
        chunk = {
            "source_name": "python_basics.txt",
            "content": "Python bir programlama dilidir.",
        }
        score = calculate_lexical_score("Python nedir?", chunk)
        self.assertGreaterEqual(score, 0.35)

    def test_lexical_score_topic_header_match(self):
        """Konu başlığı sorgudaki terimi içeriyorsa yüksek puan vermeli."""
        chunk = {
            "source_name": "notes.txt",
            "content": "[Konu: Veri Yapıları]\nListe ve Demet özellikleri.",
        }
        score = calculate_lexical_score("veri yapıları nelerdir?", chunk)
        self.assertGreaterEqual(score, 0.35)

    def test_lexical_score_irrelevant_query(self):
        """Alakasız sorguda sözcük skoru 0 olmalı."""
        chunk = {
            "source_name": "python_basics.txt",
            "content": "Python bir programlama dilidir.",
        }
        score = calculate_lexical_score("Hava durumu nasıl?", chunk)
        self.assertEqual(score, 0.0)

    def test_lexical_score_stopwords_only(self):
        """Yalnızca stopword içeren sorgular 0 dönmeli."""
        chunk = {
            "source_name": "python_basics.txt",
            "content": "Python bir programlama dilidir.",
        }
        score = calculate_lexical_score("nedir nasıl ve ile", chunk)
        self.assertEqual(score, 0.0)

    def test_lexical_score_returns_float(self):
        """Dönüş tipi float olmalı."""
        chunk = {"source_name": "test.txt", "content": "Test içeriği burada."}
        score = calculate_lexical_score("test", chunk)
        self.assertIsInstance(score, float)

    def test_lexical_score_max_capped_at_one(self):
        """Çok fazla eşleşme olsa bile skor 1.0'ı geçmemeli."""
        chunk = {
            "source_name": "python_python.txt",
            "content": "Python Python Python Python Python Python Python.",
        }
        score = calculate_lexical_score("Python Python Python", chunk)
        self.assertLessEqual(score, 1.0)

    def test_lexical_score_non_negative(self):
        """Skor her zaman 0.0 veya daha büyük olmalı."""
        chunk = {"source_name": "doc.txt", "content": "Tamamen alakasız içerik burada."}
        score = calculate_lexical_score("makine öğrenmesi nedir", chunk)
        self.assertGreaterEqual(score, 0.0)

    def test_lexical_score_content_frequency_boost(self):
        """İçerikte anahtar kelime çok tekrarlanırsa skor artmalı."""
        chunk_low = {
            "source_name": "doc.txt",
            "content": "Makine öğrenmesi hakkında kısa bir metin. Başka konular da var.",
        }
        chunk_high = {
            "source_name": "doc.txt",
            "content": "Makine öğrenmesi makine öğrenmesi makine öğrenmesi hakkında kapsamlı bilgi.",
        }
        score_low = calculate_lexical_score("makine öğrenmesi", chunk_low)
        score_high = calculate_lexical_score("makine öğrenmesi", chunk_high)
        self.assertGreater(score_high, score_low)

    def test_lexical_score_empty_query(self):
        """Boş sorgu için 0.0 dönmeli (hata fırlatmamalı)."""
        chunk = {"source_name": "test.txt", "content": "İçerik var."}
        score = calculate_lexical_score("", chunk)
        self.assertEqual(score, 0.0)

    def test_lexical_score_short_keywords_filtered(self):
        """1 karakterli kelimeler anahtar kelime sayılmamalı → 0 dönmeli."""
        chunk = {"source_name": "a.txt", "content": "Kısa kelimeler a b c d e."}
        score = calculate_lexical_score("a b c", chunk)
        self.assertEqual(score, 0.0)


class TestFormatContext(unittest.TestCase):
    """Retriever.format_context() metodu için testler."""

    def _make_mock_embedder(self):
        """Gerçek model yüklemeden basit bir mock embedder döner."""
        from unittest.mock import MagicMock
        embedder = MagicMock()
        embedder.embed.return_value = [0.1] * 384
        return embedder

    def test_format_context_empty_chunks(self):
        """Boş chunk listesi için önceden tanımlı mesaj dönmeli."""
        retriever = Retriever(self._make_mock_embedder())
        result = retriever.format_context([])
        self.assertEqual(result, "İlgili belge alıntısı bulunamadı.")

    def test_format_context_single_chunk_xml_structure(self):
        """Tek chunk için doğru XML yapısı üretilmeli."""
        retriever = Retriever(self._make_mock_embedder())
        chunks = [
            {
                "source_name": "python_basics.txt",
                "content": "Python dinamik tipli bir dildir.",
                "score": 0.85,
            }
        ]
        result = retriever.format_context(chunks)
        self.assertIn('<belge kaynak="python_basics.txt">', result)
        self.assertIn("Python dinamik tipli bir dildir.", result)
        self.assertIn("</belge>", result)

    def test_format_context_multiple_chunks_separated(self):
        """Birden fazla chunk çift satır boşluğuyla ayrılmalı."""
        retriever = Retriever(self._make_mock_embedder())
        chunks = [
            {"source_name": "doc1.txt", "content": "Birinci kaynak içeriği.", "score": 0.9},
            {"source_name": "doc2.txt", "content": "İkinci kaynak içeriği.", "score": 0.8},
        ]
        result = retriever.format_context(chunks)
        # İki belge etiketi arasında ayraç bulunmalı
        self.assertIn("</belge>", result)
        self.assertIn('<belge kaynak="doc1.txt">', result)
        self.assertIn('<belge kaynak="doc2.txt">', result)
        # İki chunk arasında çift satır boşluğu olmalı
        parts = result.split("\n\n")
        self.assertEqual(len(parts), 2)

    def test_format_context_returns_string(self):
        """format_context her zaman string dönmeli."""
        retriever = Retriever(self._make_mock_embedder())
        result = retriever.format_context([])
        self.assertIsInstance(result, str)

    def test_format_context_source_name_in_output(self):
        """Her chunk için kaynak adı XML etiketinde görünmeli."""
        retriever = Retriever(self._make_mock_embedder())
        chunks = [
            {"source_name": "rag_concepts.txt", "content": "RAG bir tasarım desenidir.", "score": 0.7},
        ]
        result = retriever.format_context(chunks)
        self.assertIn("rag_concepts.txt", result)


if __name__ == "__main__":
    unittest.main()
