"""
tests/test_retriever.py — Hibrit Arama ve Retrieval Mantığı Testleri
===================================================================
Bu testler model indirmesi gerektirmez, doğrudan hibrit arama,
sözcük puanlama ve stopword filtreleme algoritmalarını doğrular.

Çalıştır:
  .\\venv\\Scripts\\python -m pytest tests/test_retriever.py -v
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag.retriever import calculate_lexical_score, cosine_similarity


class TestRetrieverLogic(unittest.TestCase):

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


if __name__ == "__main__":
    unittest.main()
