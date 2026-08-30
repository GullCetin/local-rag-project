"""
tests/test_ingest.py — Ingestion Modülü Unit Testleri
======================================================
Dosya okuma, keşif ve chunking pipeline'ı testleri.
Model indirmesi veya ağ bağlantısı gerektirmez.

Çalıştır:
  .\\venv\\Scripts\\python -m pytest tests/test_ingest.py -v
"""

import sys
import os
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ingest import read_txt, read_document, discover_files, chunk_text


SAMPLE_DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "sample_docs")


class TestReadTxt(unittest.TestCase):
    """read_txt ve read_document fonksiyonları için testler."""

    def test_read_txt_returns_string(self):
        """read_txt bir string döndürmeli."""
        path = os.path.join(SAMPLE_DOCS_DIR, "python_basics.txt")
        if not os.path.exists(path):
            self.skipTest("python_basics.txt bulunamadı")
        result = read_txt(path)
        self.assertIsInstance(result, str)

    def test_read_txt_nonempty(self):
        """Gerçek bir .txt dosyası okununca sonuç boş olmamalı."""
        path = os.path.join(SAMPLE_DOCS_DIR, "rag_concepts.txt")
        if not os.path.exists(path):
            self.skipTest("rag_concepts.txt bulunamadı")
        result = read_txt(path)
        self.assertGreater(len(result.strip()), 0)

    def test_read_txt_turkish_content(self):
        """Türkçe içerikli dosya doğru okunmalı."""
        # Geçici Türkçe dosya oluştur
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write("Türkçe karakterler: ğüşıöç\nMerhaba dünya!")
            tmp_path = f.name

        try:
            content = read_txt(tmp_path)
            self.assertIn("ğüşıöç", content)
            self.assertIn("Merhaba", content)
        finally:
            os.unlink(tmp_path)

    def test_read_document_txt_extension(self):
        """read_document .txt dosyasını kabul etmeli."""
        path = os.path.join(SAMPLE_DOCS_DIR, "python_basics.txt")
        if not os.path.exists(path):
            self.skipTest("python_basics.txt bulunamadı")
        result = read_document(path)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_read_document_md_extension(self):
        """read_document .md dosyasını kabul etmeli."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", encoding="utf-8", delete=False
        ) as f:
            f.write("# Başlık\n\nMarkdown içeriği burada.")
            tmp_path = f.name
        try:
            result = read_document(tmp_path)
            self.assertIn("Markdown", result)
        finally:
            os.unlink(tmp_path)

    def test_read_document_nonexistent_raises(self):
        """Olmayan dosya FileNotFoundError fırlatmalı."""
        with self.assertRaises(FileNotFoundError):
            read_document("/olmayan/path/dosya.txt")

    def test_read_document_unsupported_extension_raises(self):
        """Desteklenmeyen uzantı ValueError fırlatmalı."""
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            tmp_path = f.name
        try:
            with self.assertRaises(ValueError):
                read_document(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_read_document_docx_unsupported(self):
        """DOCX formatı desteklenmemeli → ValueError."""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            tmp_path = f.name
        try:
            with self.assertRaises(ValueError):
                read_document(tmp_path)
        finally:
            os.unlink(tmp_path)


class TestDiscoverFiles(unittest.TestCase):
    """discover_files fonksiyonu için testler."""

    def test_discover_single_txt_file(self):
        """Tek .txt dosyası verilince liste tek elemanlı olmalı."""
        path = os.path.join(SAMPLE_DOCS_DIR, "python_basics.txt")
        if not os.path.exists(path):
            self.skipTest("python_basics.txt bulunamadı")
        files = discover_files(path)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith("python_basics.txt"))

    def test_discover_directory(self):
        """Klasör verilince desteklenen tüm dosyalar listelenmeli."""
        if not os.path.exists(SAMPLE_DOCS_DIR):
            self.skipTest("sample_docs dizini bulunamadı")
        files = discover_files(SAMPLE_DOCS_DIR)
        self.assertGreater(len(files), 0)
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            self.assertIn(ext, {".txt", ".md", ".pdf"})

    def test_discover_returns_list(self):
        """discover_files dönüş tipi list olmalı."""
        result = discover_files(SAMPLE_DOCS_DIR)
        self.assertIsInstance(result, list)

    def test_discover_unsupported_file_skipped(self):
        """Desteklenmeyen uzantılı tek dosya → boş liste."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Sadece .xyz dosyası olan klasör
            unsupported = os.path.join(tmpdir, "test.xyz")
            open(unsupported, "w").close()
            files = discover_files(tmpdir)
            # .xyz desteklenmediğinden boş liste dönmeli
            self.assertEqual(files, [])

    def test_discover_nonexistent_path_raises(self):
        """Olmayan yol FileNotFoundError fırlatmalı."""
        with self.assertRaises(FileNotFoundError):
            discover_files("/olmayan/dizin/veya/dosya")

    def test_discover_mixed_directory(self):
        """Karışık uzantılı klasörde sadece desteklenenleri döndürmeli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Desteklenen
            open(os.path.join(tmpdir, "a.txt"), "w").close()
            open(os.path.join(tmpdir, "b.md"), "w").close()
            # Desteklenmeyen
            open(os.path.join(tmpdir, "c.xyz"), "w").close()
            open(os.path.join(tmpdir, "d.docx"), "w").close()

            files = discover_files(tmpdir)
            filenames = [os.path.basename(f) for f in files]
            self.assertIn("a.txt", filenames)
            self.assertIn("b.md", filenames)
            self.assertNotIn("c.xyz", filenames)
            self.assertNotIn("d.docx", filenames)

    def test_discover_directory_sorted(self):
        """Klasör keşfinde dosyalar sıralı dönmeli."""
        if not os.path.exists(SAMPLE_DOCS_DIR):
            self.skipTest("sample_docs dizini bulunamadı")
        files = discover_files(SAMPLE_DOCS_DIR)
        basenames = [os.path.basename(f) for f in files]
        self.assertEqual(basenames, sorted(basenames))


class TestIngestChunkingWithRealDocs(unittest.TestCase):
    """Gerçek sample dokümanlar üzerinde chunking pipeline testi."""

    def _get_sample_doc_chunks(self, filename: str) -> list:
        """Verilen sample dosyayı okuyup chunk'lara böl."""
        path = os.path.join(SAMPLE_DOCS_DIR, filename)
        if not os.path.exists(path):
            return None
        content = read_txt(path)
        return chunk_text(content, source_name=filename)

    def test_python_basics_chunking(self):
        """python_basics.txt doğru şekilde chunk'lara bölünmeli."""
        chunks = self._get_sample_doc_chunks("python_basics.txt")
        if chunks is None:
            self.skipTest("python_basics.txt bulunamadı")
        self.assertGreater(len(chunks), 1)
        # Kaynak etiketi bulunmalı
        all_text = " ".join(chunks)
        self.assertIn("python_basics.txt", all_text)

    def test_rag_concepts_chunking(self):
        """rag_concepts.txt doğru şekilde chunk'lara bölünmeli."""
        chunks = self._get_sample_doc_chunks("rag_concepts.txt")
        if chunks is None:
            self.skipTest("rag_concepts.txt bulunamadı")
        self.assertGreater(len(chunks), 1)
        all_text = " ".join(chunks)
        # RAG temel kavramları chunk'larda geçmeli
        self.assertIn("RAG", all_text)

    def test_machine_learning_chunking(self):
        """machine_learning.txt doğru şekilde chunk'lara bölünmeli."""
        chunks = self._get_sample_doc_chunks("machine_learning.txt")
        if chunks is None:
            self.skipTest("machine_learning.txt bulunamadı")
        self.assertGreater(len(chunks), 1)
        all_text = " ".join(chunks)
        self.assertIn("makine", all_text.lower())

    def test_vector_databases_chunking(self):
        """vector_databases.txt doğru şekilde chunk'lara bölünmeli."""
        chunks = self._get_sample_doc_chunks("vector_databases.txt")
        if chunks is None:
            self.skipTest("vector_databases.txt bulunamadı")
        self.assertGreater(len(chunks), 1)
        all_text = " ".join(chunks)
        self.assertIn("Chroma", all_text)

    def test_all_sample_docs_produce_chunks(self):
        """Tüm sample doclar en az 1 chunk üretmeli."""
        if not os.path.exists(SAMPLE_DOCS_DIR):
            self.skipTest("sample_docs dizini bulunamadı")
        files = discover_files(SAMPLE_DOCS_DIR)
        for file_path in files:
            fname = os.path.basename(file_path)
            content = read_txt(file_path)
            chunks = chunk_text(content, source_name=fname)
            self.assertGreater(len(chunks), 0, f"{fname} hiç chunk üretmedi!")


if __name__ == "__main__":
    unittest.main()
