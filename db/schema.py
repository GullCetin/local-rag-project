"""
db/schema.py — SQLite Şema Tanımları
=====================================
Bu modül veritabanı tablolarının SQL tanımlarını içerir.
Tablo yapısı değişirse buradan güncellenir.

TABLO: documents
  Belge chunk'larını ve embedding vektörlerini saklar.

  id          : Otomatik artan birincil anahtar
  source_name : Belgenin dosya adı (kaynak gösterimi için)
  chunk_index : Belge içindeki sıra numarası (0'dan başlar)
  content     : Ham metin içeriği
  embedding   : JSON formatında saklanmış float listesi
  created_at  : Kaydın eklendiği zaman
"""

CREATE_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER   PRIMARY KEY AUTOINCREMENT,
    source_name TEXT      NOT NULL,
    chunk_index INTEGER   NOT NULL,
    content     TEXT      NOT NULL,
    embedding   TEXT      NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_name, chunk_index)
);
"""

# Kaynak adı üzerinden hızlı arama için index
CREATE_SOURCE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_source_name ON documents(source_name);
"""

# Tüm şema ifadelerini sırayla uygula
ALL_SCHEMA_STATEMENTS = [
    CREATE_DOCUMENTS_TABLE,
    CREATE_SOURCE_INDEX,
]
