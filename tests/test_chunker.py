"""
tests/test_chunker.py — Paragraf Bazlı Chunker Unit Testleri (Genişletilmiş)
============================================================================
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
from config import CHUNK_MIN_CHARS, CHUNK_MAX_CHARS


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
            self.assertLessEqual(len(chunk), CHUNK_MAX_CHARS)

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

    # -----------------------------------------------------------------------
    # YENİ TESTLER
    # -----------------------------------------------------------------------

    def test_context_prefix_with_source_name(self):
        """source_name verilince chunk içinde belge etiketi görünmeli."""
        text = "Bu bir içerik paragrafıdır ve oldukça uzundur. " * 3
        chunks = chunk_text(text, source_name="test_doc.txt")
        self.assertTrue(len(chunks) > 0)
        self.assertIn("test_doc.txt", chunks[0])
        self.assertIn("Belge:", chunks[0])

    def test_context_prefix_without_source_name(self):
        """source_name verilmezse chunk'ta 'Belge:' etiketi olmamalı."""
        text = "Bu bir içerik paragrafıdır ve oldukça uzundur. " * 3
        chunks = chunk_text(text, source_name="")
        self.assertTrue(len(chunks) > 0)
        # source_name boş olduğunda sadece section varsa etiket eklenir
        # Başlık yoksa etiket hiç eklenmemeli
        for chunk in chunks:
            self.assertNotIn("Belge:", chunk)

    def test_markdown_heading_detection(self):
        """# ile başlayan satır başlık olarak algılanmalı ve section takip edilmeli."""
        text = "# Python Temelleri\n\nPython dinamik tipli bir dildir ve oldukça esnektir. " * 3
        chunks = chunk_text(text, source_name="python.txt")
        self.assertTrue(len(chunks) > 0)
        # Konu bağlamı chunk'ta bulunmalı
        all_text = " ".join(chunks)
        self.assertIn("Python Temelleri", all_text)

    def test_markdown_heading_stripped_from_content(self):
        """Başlık satırının # işareti chunk içeriğinde doğrudan görünmemeli (Konu: etiketine dönüşmeli)."""
        text = "# Başlık Satırı\n\nAçıklama metni burada yer almaktadır. Uzun bir metin. " * 3
        chunks = chunk_text(text)
        for chunk in chunks:
            # Ham "# Başlık Satırı" ifadesi chunk'ta çıkmamalı,
            # bunun yerine [Konu: Başlık Satırı] formatında prefix'e dönüşmeli
            # En azından chunk, satır başında ham # işaretiyle başlamamalı
            self.assertFalse(
                chunk.strip().startswith("#"),
                f"Chunk ham # işaretiyle başlıyor: {chunk[:60]!r}"
            )

    def test_section_context_injected_after_heading(self):
        """Başlıktan sonraki paragraflarda 'Konu:' etiketi bulunmalı."""
        heading_text = "## Veri Yapıları\n\nListe sıralı değiştirilebilir öğe koleksiyonudur. " * 2
        chunks = chunk_text(heading_text, source_name="doc.txt")
        self.assertTrue(len(chunks) > 0)
        all_text = " ".join(chunks)
        self.assertIn("Veri Yapıları", all_text)

    def test_unicode_turkish_chars(self):
        """Türkçe karakterler (ğ, ü, ş, ı, ö, ç) doğru işlenmeli."""
        turkish_text = (
            "Türkçe karakterler: ğüşıöç bunlar doğru işlenmeli. "
            "Üniversitede öğrenciler çalışmalar yapar. " * 4
        )
        chunks = chunk_text(turkish_text, source_name="türkçe.txt")
        self.assertTrue(len(chunks) > 0)
        all_text = " ".join(chunks)
        self.assertIn("Türkçe", all_text)
        self.assertIn("öğrenciler", all_text)

    def test_split_long_paragraph_min_chars_respected(self):
        """Uzun paragraf bölününce alt parçalar CHUNK_MIN_CHARS'tan küçük olmamalı."""
        # Çok uzun tek cümle
        long_para = "Uzun bir kelime. " * 200  # ~3400 karakter
        chunks = chunk_text(long_para)
        for chunk in chunks:
            # Her chunk strip edilmiş içeriği CHUNK_MIN_CHARS'tan büyük olmalı
            self.assertGreaterEqual(len(chunk.strip()), CHUNK_MIN_CHARS)

    def test_multiple_headings_track_last_section(self):
        """Birden fazla başlık varsa paragraflar doğru section'a bağlanmalı."""
        # Uzun içerikler kullan ki MIN_CHARS filtresi etkilemesin
        long_content = "Bu bölümün içeriği oldukça detaylı açıklamalar içermektedir. " * 4
        text = (
            f"# Birinci Bölüm\n\n{long_content}\n\n"
            f"## İkinci Bölüm\n\n{long_content}"
        )
        chunks = chunk_text(text, source_name="test.txt")
        self.assertTrue(len(chunks) >= 2, f"Beklenen en az 2 chunk, bulunan: {len(chunks)}")
        # Tüm chunk'lardaki metinde her iki bölüm adı geçmeli
        all_text = " ".join(chunks)
        self.assertIn("Birinci Bölüm", all_text)
        self.assertIn("İkinci Bölüm", all_text)

    def test_returns_list_type(self):
        """Dönüş tipi her zaman list olmalı."""
        result = chunk_text("Metin içeriği. " * 5)
        self.assertIsInstance(result, list)

    def test_chunk_text_with_real_sample_doc(self):
        """Gerçek sample doc üzerinde chunking doğru çalışmalı."""
        sample_path = os.path.join(
            os.path.dirname(__file__), "..", "docs", "sample_docs", "python_basics.txt"
        )
        if not os.path.exists(sample_path):
            self.skipTest("python_basics.txt bulunamadı")
        with open(sample_path, "r", encoding="utf-8") as f:
            text = f.read()
        chunks = chunk_text(text, source_name="python_basics.txt")
        # Dosyada birden fazla paragraf var → birden fazla chunk üretilmeli
        self.assertGreater(len(chunks), 1)
        # Tüm chunk'lar minimum boyut şartını karşılamalı
        for chunk in chunks:
            self.assertGreaterEqual(len(chunk.strip()), CHUNK_MIN_CHARS)
        # Tüm chunk'lar maksimum boyut şartını karşılamalı
        for chunk in chunks:
            self.assertLessEqual(len(chunk), CHUNK_MAX_CHARS + 20)  # +20 prefix toleransı


    def test_noise_lines_filtered(self):
        """URL-slug benzeri gürültü satırları (resim adları vb.) chunk'ta yer almamalı."""
        text = (
            "5. Pilotlar havada uyur mu?\n"
            "Pilot-Uyku\n"
            "Evet, pilotlar içeride uyuyorlar. Ancak bu uyku en fazla 10 dakikalık bir kestirme.\n\n"
            "Ucuslarla-Ilgili-Bilinmeyenler\n"
            "Başka bir paragraf da burayla ilgilidir ve yeterince uzundur. " * 3
        )
        chunks = chunk_text(text, source_name="ucuslar.txt")
        all_text = " ".join(chunks)
        # Gürültü satırları chunk'ta çıkmamalı
        self.assertNotIn("Pilot-Uyku", all_text)
        self.assertNotIn("Ucuslarla-Ilgili-Bilinmeyenler", all_text)
        # Ama gerçek içerik korunmalı
        self.assertIn("10 dakika", all_text)

    def test_numbered_section_sets_context(self):
        """Numaralı bölüm başlıkları (ör: '5. Pilotlar havada uyur mu?') Konu bağlamı ayarlamalı."""
        text = (
            "5. Pilotlar havada uyur mu?\n"
            "Evet, pilotlar içeride uyuyorlar. Bu uyku en fazla 10 dakikalık bir kestirme halinde.\n\n"
            "Kalkıştan sonra otomatik pilota geçilir ve bu pek bir sorun teşkil etmez."
        )
        chunks = chunk_text(text, source_name="ucuslar.txt")
        self.assertTrue(len(chunks) > 0, "En az bir chunk üretilmeli")
        all_text = " ".join(chunks)
        # Bölüm başlığı Konu: bağlamına dönüşmeli
        self.assertIn("Pilotlar havada uyur mu", all_text)


if __name__ == "__main__":
    unittest.main()
