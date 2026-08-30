"""
tests/test_db_manager.py — SQLite Veritabanı Yöneticisi Unit Testleri
======================================================================
Bu testler gerçek bir geçici SQLite veritabanı kullanır;
model indirmesi veya ağ bağlantısı gerektirmez.

Her test kendi izole geçici DB'si üzerinde çalışır (tearDown'da temizlenir).

Çalıştır:
  .\\venv\\Scripts\\python -m pytest tests/test_db_manager.py -v
"""

import sys
import os
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestDBManager(unittest.TestCase):
    """
    db/manager.py fonksiyonları için izole geçici DB testleri.
    Her test, config.DB_PATH'i geçici dosyaya yönlendirerek
    gerçek veri tabanını kirletmez.
    """

    def setUp(self):
        """Her testten önce geçici bir SQLite dosyası oluştur ve DB_PATH'i güncelle."""
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp_path = self.tmp.name
        self.tmp.close()

        # DB_PATH'i geçici dosyaya yönlendir
        self.patcher = patch("config.DB_PATH", self.tmp_path)
        self.patcher.start()

        # db.manager modülünü şimdi import et (patch aktifken)
        import importlib
        import db.manager as mgr_module
        importlib.reload(mgr_module)
        self.mgr = mgr_module

        # DB'yi başlat
        self.mgr.initialize_db()

    def tearDown(self):
        """Her testten sonra geçici dosyayı temizle."""
        self.patcher.stop()
        try:
            os.unlink(self.tmp_path)
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # initialize_db
    # -----------------------------------------------------------------------
    def test_initialize_db_creates_file(self):
        """initialize_db çağrısı DB dosyasını oluşturmalı."""
        self.assertTrue(os.path.exists(self.tmp_path))

    def test_initialize_db_creates_documents_table(self):
        """'documents' tablosu oluşturulmuş olmalı."""
        conn = sqlite3.connect(self.tmp_path)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='documents'"
        )
        tables = [row[0] for row in cur.fetchall()]
        conn.close()
        self.assertIn("documents", tables)

    def test_initialize_db_idempotent(self):
        """initialize_db iki kez çağrılırsa hata fırlatmamalı."""
        try:
            self.mgr.initialize_db()
            self.mgr.initialize_db()
        except Exception as e:
            self.fail(f"initialize_db iki kez çalıştırılınca hata oluştu: {e}")

    # -----------------------------------------------------------------------
    # save_chunk / get_all_chunks
    # -----------------------------------------------------------------------
    def test_save_and_retrieve_single_chunk(self):
        """Kaydedilen tek chunk geri alınabilmeli."""
        embedding = [0.1, 0.2, 0.3]
        self.mgr.save_chunk("test.txt", 0, "Test içeriği burada.", embedding)

        chunks = self.mgr.get_all_chunks()
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["source_name"], "test.txt")
        self.assertEqual(chunks[0]["content"], "Test içeriği burada.")
        self.assertEqual(chunks[0]["chunk_index"], 0)
        self.assertAlmostEqual(chunks[0]["embedding"][0], 0.1, places=5)

    def test_upsert_behavior(self):
        """Aynı (source_name, chunk_index) ile tekrar kayıt → güncelleme yapılmalı."""
        self.mgr.save_chunk("doc.txt", 0, "İlk içerik.", [0.1, 0.2])
        self.mgr.save_chunk("doc.txt", 0, "Güncellenmiş içerik.", [0.3, 0.4])

        chunks = self.mgr.get_all_chunks()
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["content"], "Güncellenmiş içerik.")

    def test_save_chunks_batch(self):
        """Batch kayıt doğru sayıda chunk eklemeli."""
        batch = [
            ("batch_doc.txt", 0, "Birinci chunk.", [0.1, 0.2]),
            ("batch_doc.txt", 1, "İkinci chunk.", [0.3, 0.4]),
            ("batch_doc.txt", 2, "Üçüncü chunk.", [0.5, 0.6]),
        ]
        self.mgr.save_chunks_batch(batch)
        count = self.mgr.get_chunk_count()
        self.assertEqual(count, 3)

    def test_embedding_stored_and_retrieved_as_list(self):
        """Embedding JSON olarak kaydedilip float listesi olarak geri alınmalı."""
        embedding = [0.11, 0.22, 0.33, 0.44]
        self.mgr.save_chunk("emb_test.txt", 0, "Embedding testi.", embedding)
        chunks = self.mgr.get_all_chunks()
        retrieved_emb = chunks[0]["embedding"]
        self.assertIsInstance(retrieved_emb, list)
        for orig, retr in zip(embedding, retrieved_emb):
            self.assertAlmostEqual(orig, retr, places=5)

    # -----------------------------------------------------------------------
    # get_chunk_count
    # -----------------------------------------------------------------------
    def test_get_chunk_count_empty_db(self):
        """Boş DB'de chunk sayısı 0 olmalı."""
        self.assertEqual(self.mgr.get_chunk_count(), 0)

    def test_get_chunk_count_after_inserts(self):
        """Eklenen chunk sayısıyla count eşleşmeli."""
        for i in range(5):
            self.mgr.save_chunk("count_test.txt", i, f"Chunk {i} içeriği burada.", [0.1])
        self.assertEqual(self.mgr.get_chunk_count(), 5)

    # -----------------------------------------------------------------------
    # get_sources
    # -----------------------------------------------------------------------
    def test_get_sources_returns_unique_names(self):
        """get_sources tekrarsız kaynak adlarını dönmeli."""
        self.mgr.save_chunk("doc_a.txt", 0, "İçerik A1.", [0.1])
        self.mgr.save_chunk("doc_a.txt", 1, "İçerik A2.", [0.2])
        self.mgr.save_chunk("doc_b.txt", 0, "İçerik B.", [0.3])

        sources = self.mgr.get_sources()
        self.assertEqual(len(sources), 2)
        self.assertIn("doc_a.txt", sources)
        self.assertIn("doc_b.txt", sources)

    def test_get_sources_empty_db(self):
        """Boş DB'de boş liste dönmeli."""
        sources = self.mgr.get_sources()
        self.assertEqual(sources, [])

    def test_get_sources_returns_list(self):
        """get_sources dönüş tipi list olmalı."""
        result = self.mgr.get_sources()
        self.assertIsInstance(result, list)

    # -----------------------------------------------------------------------
    # clear_source
    # -----------------------------------------------------------------------
    def test_clear_source_removes_correct_chunks(self):
        """clear_source yalnızca belirtilen kaynağın chunk'larını silmeli."""
        self.mgr.save_chunk("keep.txt", 0, "Silinmeyecek.", [0.1])
        self.mgr.save_chunk("delete.txt", 0, "Silinecek.", [0.2])
        self.mgr.save_chunk("delete.txt", 1, "Bu da silinecek.", [0.3])

        deleted = self.mgr.clear_source("delete.txt")
        self.assertEqual(deleted, 2)

        chunks = self.mgr.get_all_chunks()
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["source_name"], "keep.txt")

    def test_clear_source_nonexistent_returns_zero(self):
        """Olmayan kaynak silinmeye çalışılırsa 0 dönmeli."""
        deleted = self.mgr.clear_source("olmayan_dosya.txt")
        self.assertEqual(deleted, 0)

    def test_clear_source_returns_int(self):
        """clear_source dönüş tipi int olmalı."""
        self.mgr.save_chunk("test.txt", 0, "İçerik.", [0.1])
        result = self.mgr.clear_source("test.txt")
        self.assertIsInstance(result, int)

    # -----------------------------------------------------------------------
    # clear_all
    # -----------------------------------------------------------------------
    def test_clear_all_removes_everything(self):
        """clear_all tüm chunk'ları silmeli."""
        for i in range(3):
            self.mgr.save_chunk("all_test.txt", i, f"Chunk {i}.", [0.1])
        self.mgr.clear_all()
        self.assertEqual(self.mgr.get_chunk_count(), 0)

    # -----------------------------------------------------------------------
    # get_all_chunks sıralama
    # -----------------------------------------------------------------------
    def test_get_all_chunks_ordered(self):
        """get_all_chunks source_name ve chunk_index'e göre sıralı dönmeli."""
        self.mgr.save_chunk("b_doc.txt", 0, "B chunk 0.", [0.1])
        self.mgr.save_chunk("a_doc.txt", 1, "A chunk 1.", [0.2])
        self.mgr.save_chunk("a_doc.txt", 0, "A chunk 0.", [0.3])

        chunks = self.mgr.get_all_chunks()
        self.assertEqual(chunks[0]["source_name"], "a_doc.txt")
        self.assertEqual(chunks[0]["chunk_index"], 0)
        self.assertEqual(chunks[1]["chunk_index"], 1)
        self.assertEqual(chunks[2]["source_name"], "b_doc.txt")


if __name__ == "__main__":
    unittest.main()
