"""
rag/retriever.py — Hibrit Arama & Retrieval Motoru (rules.txt: Adım 8)
========================================================================
Bu modül, kullanıcının sorgusunu hem semantik (Dense Vector / Cosine Similarity)
hem de sözcüksel/başlık (Lexical Match) olarak skorlayıp en ilgili bağlamı sunar.

Kurumsal RAG İlkeleri (rules.txt Adım 8):
  - Hibrit Arama: Semantik (0.60) + Sözcüksel/Kavramsal (0.40)
  - Şeffaf Loglama: Neden bu chunk seçildi, skoru neydi?
  - Bağlam Zenginleştirme: XML tabanlı temiz <belge> formatı.
"""

import logging
import re
from typing import Optional

import numpy as np

from config import (
    HYBRID_DENSE_WEIGHT,
    HYBRID_LEXICAL_WEIGHT,
    SCORE_THRESHOLD,
    TOP_K_CHUNKS,
)
from db.manager import get_all_chunks
from rag.embedder import Embedder

logger = logging.getLogger(__name__)


def calculate_lexical_score(query: str, chunk: dict) -> float:
    """
    Sorgu ile chunk arasındaki sözcüksel, başlık ve tam kelime (exact word) uyumunu hesaplar [0.0 - 1.0].
    
    Kurumsal RAG İlkesi:
      Semantik aramanın zayıf kalabildiği spesifik teknik terimleri (örn. 'def', 'class', 'RAG', 'ANN', 'SQL')
      tam sözcük eşleşmesi (whole word match) ile anında tespit eder ve en üst sıraya taşır.
    """
    words = re.findall(r"\b[a-zA-ZçğıöşüÇĞİÖŞÜ0-9_]+\b", query.lower())
    stop_words = {
        "nedir", "nelerdir", "nasıl", "ve", "ile", "bir", "mi", "mı",
        "mu", "mü", "bu", "şu", "hakkında", "için", "ne", "var", "yok",
        "hangi", "kadar", "olan", "olarak", "ise", "diye", "göre",
        "neler", "nerede", "kimdir", "bunu", "buna", "şeylerin", "tadı",
        "daha", "en", "çok", "az", "gibi"
    }
    keywords = [w for w in words if w not in stop_words and len(w) >= 2]
    if not keywords:
        return 0.0

    content_lower = chunk["content"].lower()
    source_lower = chunk["source_name"].lower()

    score = 0.0
    for kw in keywords:
        # 1. Tam sözcük eşleşmesi kontrolü (\bkw\b)
        exact_pattern = re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
        exact_matches = len(exact_pattern.findall(content_lower))

        # 2. Dosya adında eşleşme
        if kw in source_lower:
            score += 0.30

        # 3. Başlık satırında ([Konu: ...] veya ilk satır) eşleşme
        first_line = content_lower.split("\n")[0] if "\n" in content_lower else content_lower
        if kw in first_line:
            score += 0.40

        # 4. Tam sözcük (Exact Whole Word) eşleşme ağırlığı (Def, Class, RAG gibi kritik terimler için)
        if exact_matches > 0:
            score += min(0.60, 0.40 + (exact_matches - 1) * 0.10)
        elif kw in content_lower:
            score += 0.15

    return min(1.0, score)


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    İki vektör arasındaki cosine similarity değerini [-1.0, 1.0] hesaplar.
    """
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


class Retriever:
    """
    SQLite'taki chunk'lar üzerinde Hibrit Arama (Dense Vector + Lexical) yapan motor.
    """

    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder

    def get_top_chunks(
        self,
        query: str,
        top_k: int = TOP_K_CHUNKS,
    ) -> list[dict]:
        """
        Verilen sorgu için en ilgili chunk'ları hibrit puanlama ile döner.
        rules.txt Adım 8: Şeffaf loglama ve doğru sıralama (reranking).
        """
        if not query or not query.strip():
            raise ValueError("Sorgu boş olamaz.")

        clean_query = query.strip()

        # 1. Sorguyu embed et
        query_vector = self._embedder.embed(clean_query)

        # 2. DB'deki tüm chunk'ları al
        all_chunks = get_all_chunks()

        if not all_chunks:
            logger.warning("Veritabanı boş. Önce 'python ingest.py' çalıştırın.")
            return []

        # 3. Hibrit skor hesapla
        scored = []
        for chunk in all_chunks:
            dense_score = max(0.0, cosine_similarity(query_vector, chunk["embedding"]))
            lexical_score = calculate_lexical_score(clean_query, chunk)
            hybrid_score = (HYBRID_DENSE_WEIGHT * dense_score) + (HYBRID_LEXICAL_WEIGHT * lexical_score)

            scored.append({
                "id": chunk["id"],
                "source_name": chunk["source_name"],
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "score": hybrid_score,
                "dense_score": dense_score,
                "lexical_score": lexical_score,
            })

        # 4. Skora göre azalan sırala
        scored.sort(key=lambda x: x["score"], reverse=True)

        # 5. Eşik filtreleme
        filtered = [c for c in scored if c["score"] >= SCORE_THRESHOLD]

        if not filtered:
            top_candidate_score = scored[0]["score"] if scored else 0.0
            logger.warning(
                f"Hiçbir chunk SCORE_THRESHOLD ({SCORE_THRESHOLD}) eşiğini geçemedi. "
                f"En yüksek skor: {top_candidate_score:.4f}"
            )
            return []

        top_chunks = filtered[:top_k]

        # rules.txt Adım 10: Şeffaf Retrieval Loglama
        logger.info(
            f"Retrieval Raporu (Top-{len(top_chunks)}): "
            f"En yüksek skor: {top_chunks[0]['score']:.4f} (Dense: {top_chunks[0]['dense_score']:.4f}, "
            f"Lexical: {top_chunks[0]['lexical_score']:.4f}) -> {top_chunks[0]['source_name']}"
        )

        return top_chunks

    def format_context(self, chunks: list[dict]) -> str:
        """
        Seçilen chunk'ları LLM için temiz, okunabilir ve gürültüsüz bir metne dönüştürür.
        """
        if not chunks:
            return ""

        blocks = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source_name", "belge")
            content = chunk.get("content", "").strip()
            # [Belge: ... | Konu: ...] başlığını kaldırıp saf içeriği alalım
            clean_content = re.sub(r"^\[Belge:[^\]]+\]\s*", "", content).strip()
            blocks.append(f"--- Kaynak {i} ({source}) ---\n{clean_content}")

        return "\n\n".join(blocks)
