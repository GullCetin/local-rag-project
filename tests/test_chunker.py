"""
tests/test_chunker.py — Paragraf Bazlı Chunker Unit Testleri
============================================================
Bu testler ağ/model bağlantısı gerektirmez.
Sadece chunking mantığını doğrular.

Çalıştır:
  .\\venv\\Scripts\\python -m pytest tests/test_chunker.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from ingest import chunk_text


class TestChunkText(unittest.TestCase):

    def test_empty_string_returns_empty_list(self):
        """Boş metin → boş liste."""
        self.assertEqual(chunk_text(""), [])
        self.assertEqual(chunk_text("   "), [])

    def test_single_paragraph(self):
        """Tek paragraf → tek chunk."""
        text = "Bu bir test paragrafıdır ve yeterince uzundur. " * 3
        chunks = chunk_text(text)
        self.assertEqual(len(chunks), 1)
        self.assertIn("test paragrafı", chunks[0])

    def test_multiple_paragraphs(self):
        """İki paragraf çift satır sonu ile ayrılmış → iki chunk."""
        para1 = "Birinci paragraf. " * 5
        para2 = "İkinci paragraf. " * 5
        text = para1 + "\n\n" + para2
        chunks = chunk_text(text)
        self.assertEqual(len(chunks), 2)

    def test_short_paragraphs_filtered(self):
        """CHUNK_MIN_CHARS'tan kısa paragraflar filtrelenmeli."""
        text = "Kısa.\n\nBu paragraf yeterince uzundur ve filtrelenmemeli. " * 3
        chunks = chunk_text(text)
        for chunk in chunks:
            self.assertGreaterEqual(len(chunk), 50)

    def test_long_paragraph_is_split(self):
        """CHUNK_MAX_CHARS'tan uzun paragraflar bölünmeli."""
        long_para = "Bu çok uzun bir cümle. " * 100  # ~2400 karakter
        chunks = chunk_text(long_para)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 800)

    def test_chunks_are_stripped(self):
        """Her chunk başında/sonunda boşluk olmamalı."""
        text = "  Temiz bir paragraf.  \n\n  Bir diğer temiz paragraf.  " * 2
        chunks = chunk_text(text)
        for chunk in chunks:
            self.assertEqual(chunk, chunk.strip())

    def test_preserves_content(self):
        """Chunk'lar orijinal içeriği korumalı."""
        keyword = "UNIK_KELIME_XYZ"
        text = f"Bu paragrafta {keyword} var. " * 5
        chunks = chunk_text(text)
        all_text = " ".join(chunks)
        self.assertIn(keyword, all_text)


if __name__ == "__main__":
    unittest.main()
