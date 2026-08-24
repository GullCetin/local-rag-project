"""
db/manager.py — SQLite Veritabanı Yöneticisi
=============================================
Bu modül, veritabanı bağlantısını yönetir ve CRUD işlemlerini sağlar.

Neden bu şekilde tasarlandı:
  - Tüm DB işlemleri tek bir yerde → Separation of Concerns
  - Parameterized queries kullanılır → SQL injection'a karşı güvenli
  - Context manager ile bağlantı yönetimi → kaynak sızıntısı yok
"""

import json
import logging
import os
import sqlite3
from typing import Optional

from config import DB_PATH
from db.schema import ALL_SCHEMA_STATEMENTS

logger = logging.getLogger(__name__)


def _get_connection() -> sqlite3.Connection:
    """
    Veritabanına bağlantı döner.
    Veritabanı dizini yoksa otomatik oluşturur.
    """
    db_dir = os.path.dirname(DB_PATH)
    os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    # Sözlük benzeri row erişimi için
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db() -> None:
    """
    Veritabanını ve tabloları oluşturur.
    Tablolar zaten varsa dokunmaz (IF NOT EXISTS).
    Uygulama başlangıcında çağrılmalıdır.
    """
    with _get_connection() as conn:
        for statement in ALL_SCHEMA_STATEMENTS:
            conn.execute(statement)
        conn.commit()
    logger.info(f"Veritabanı hazır: {DB_PATH}")


def save_chunk(
    source_name: str,
    chunk_index: int,
    content: str,
    embedding: list[float],
) -> None:
    """
    Bir belge chunk'ını ve embedding vektörünü veritabanına kaydeder.

    Aynı (source_name, chunk_index) çifti zaten varsa günceller (UPSERT).
    Bu sayede ingestion scripti güvenle tekrar çalıştırılabilir.

    Args:
        source_name : Kaynak belgenin dosya adı (örn. "python_notes.txt")
        chunk_index : Belgedeki sıra numarası (0'dan başlar)
        content     : Ham metin içeriği
        embedding   : Float listesi olarak embedding vektörü
    """
    embedding_json = json.dumps(embedding)

    sql = """
        INSERT INTO documents (source_name, chunk_index, content, embedding)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(source_name, chunk_index)
        DO UPDATE SET
            content   = excluded.content,
            embedding = excluded.embedding,
            created_at = CURRENT_TIMESTAMP
    """

    with _get_connection() as conn:
        conn.execute(sql, (source_name, chunk_index, content, embedding_json))
        conn.commit()


def save_chunks_batch(
    chunks: list[tuple[str, int, str, list[float]]],
) -> None:
    """
    Birden fazla chunk'ı tek seferde kaydeder (performans için batch insert).

    Args:
        chunks: (source_name, chunk_index, content, embedding) tuple listesi
    """
    sql = """
        INSERT INTO documents (source_name, chunk_index, content, embedding)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(source_name, chunk_index)
        DO UPDATE SET
            content   = excluded.content,
            embedding = excluded.embedding,
            created_at = CURRENT_TIMESTAMP
    """
    rows = [
        (src, idx, content, json.dumps(emb))
        for src, idx, content, emb in chunks
    ]

    with _get_connection() as conn:
        conn.executemany(sql, rows)
        conn.commit()

    logger.info(f"{len(rows)} chunk kaydedildi.")


def get_all_chunks() -> list[dict]:
    """
    Veritabanındaki tüm chunk'ları döner.
    Embedding vektörleri JSON'dan float listesine geri dönüştürülür.

    Returns:
        Her biri {"id", "source_name", "chunk_index", "content", "embedding"} içeren dict listesi
    """
    sql = "SELECT id, source_name, chunk_index, content, embedding FROM documents ORDER BY source_name, chunk_index"

    with _get_connection() as conn:
        rows = conn.execute(sql).fetchall()

    return [
        {
            "id": row["id"],
            "source_name": row["source_name"],
            "chunk_index": row["chunk_index"],
            "content": row["content"],
            "embedding": json.loads(row["embedding"]),
        }
        for row in rows
    ]


def get_chunk_count() -> int:
    """Veritabanındaki toplam chunk sayısını döner."""
    with _get_connection() as conn:
        result = conn.execute("SELECT COUNT(*) FROM documents").fetchone()
    return result[0]


def get_sources() -> list[str]:
    """Veritabanında kayıtlı tüm benzersiz kaynak belge adlarını döner."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT source_name FROM documents ORDER BY source_name"
        ).fetchall()
    return [row["source_name"] for row in rows]


def clear_source(source_name: str) -> int:
    """
    Belirtilen kaynak belginin tüm chunk'larını siler.

    Args:
        source_name: Silinecek kaynak belgenin adı

    Returns:
        Silinen kayıt sayısı
    """
    with _get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM documents WHERE source_name = ?", (source_name,)
        )
        conn.commit()
    deleted = cursor.rowcount
    logger.info(f"'{source_name}' için {deleted} chunk silindi.")
    return deleted


def clear_all() -> None:
    """Veritabanındaki tüm chunk'ları siler. Dikkatli kullan!"""
    with _get_connection() as conn:
        conn.execute("DELETE FROM documents")
        conn.commit()
    logger.warning("Tüm chunk'lar silindi.")
