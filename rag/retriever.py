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


def explain_lexical_score(query: str, chunk: dict) -> dict:
    """
    Sorgu ile chunk arasındaki sözcüksel eşleşmelerin matematiksel detay dökümünü döner.
    
    Tasarım İlkeleri (Phase 3):
      1. Ana Bileşen: Term Coverage (eşleşen anahtar kelime / toplam anahtar kelime) -> %65
      2. Başlık / İlk Satır Bonusu: +%15 (en fazla)
      3. Tam İfade / Bütün Terimler Bonusu: +%10 (en fazla)
      4. Frekans / Tekrar Bonusu: +%10 (en fazla)
      5. Dosya Adı: Ana skora dahil EDİLMEZ, sadece metadata/debug olarak tutulur.
      6. Skor kesinlikle [0.0, 1.0] aralığında normalize edilir.
    """
    words = re.findall(r"\b[a-zA-ZçğıöşüÇĞİÖŞÜ0-9_]+\b", query.lower())
    stop_words = {
        "nedir", "nelerdir", "nasıl", "ve", "ile", "bir", "mi", "mı",
        "mu", "mü", "bu", "şu", "hakkında", "için", "ne", "var", "yok",
        "hangi", "kadar", "olan", "olarak", "ise", "diye", "göre",
        "neler", "nerede", "kimdir", "bunu", "buna", "şeylerin", "tadı",
        "daha", "en", "çok", "az", "gibi"
    }
    keywords = list(dict.fromkeys([w for w in words if w not in stop_words and len(w) >= 2]))
    if not keywords:
        return {
            "query": query,
            "keywords": [],
            "matched_keywords": [],
            "filename_matches": [],
            "title_matches": [],
            "exact_matches": {},
            "partial_matches": [],
            "term_coverage": 0.0,
            "title_bonus": 0.0,
            "phrase_bonus": 0.0,
            "freq_bonus": 0.0,
            "raw_score": 0.0,
            "final_score": 0.0,
        }

    content_lower = chunk.get("content", "").lower()
    source_lower = chunk.get("source_name", "").lower()
    first_line = content_lower.split("\n")[0] if "\n" in content_lower else content_lower

    total_keywords = len(keywords)
    matched_keywords = []
    filename_matches = []
    title_matches = []
    exact_matches = {}
    partial_matches = []
    total_occurrences = 0

    # 1. Her anahtar kelime için içerik ve başlık taraması
    for kw in keywords:
        if kw in source_lower:
            filename_matches.append(kw)

        exact_pattern = re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
        occurrences = len(exact_pattern.findall(content_lower))

        in_title = bool(re.search(rf"\b{re.escape(kw)}\b", first_line, re.IGNORECASE)) or (kw in first_line)
        if in_title:
            title_matches.append(kw)

        if occurrences > 0:
            exact_matches[kw] = occurrences
            total_occurrences += occurrences
            matched_keywords.append(kw)
        elif kw in content_lower:
            partial_matches.append(kw)
            matched_keywords.append(kw)

    # 2. Term Coverage (Ana Skor): Eşleşen kelime oranı * 0.65
    unique_matched = len(set(matched_keywords))
    coverage_ratio = unique_matched / total_keywords
    coverage_score = coverage_ratio * 0.65

    # 3. Başlık / İlk Satır Bonusu (+0.15 max)
    title_bonus = (len(set(title_matches)) / total_keywords) * 0.15 if title_matches else 0.0

    # 4. Tam İfade / Tüm Kelimelerin Birlikte Bulunması Bonusu (+0.10)
    phrase_bonus = 0.0
    if total_keywords >= 2:
        clean_phrase = " ".join(keywords)
        if clean_phrase in content_lower or unique_matched == total_keywords:
            phrase_bonus = 0.10
    elif total_keywords == 1 and unique_matched == 1:
        phrase_bonus = 0.10

    # 5. Frekans Bonusu (+0.10 max) - birden çok geçiyorsa
    freq_bonus = 0.0
    if total_occurrences > 1:
        freq_bonus = min(0.10, (total_occurrences - 1) * 0.02)

    raw_score = coverage_score + title_bonus + phrase_bonus + freq_bonus
    final_score = min(1.0, max(0.0, raw_score))

    return {
        "query": query,
        "keywords": keywords,
        "matched_keywords": matched_keywords,
        "filename_matches": filename_matches,
        "title_matches": title_matches,
        "exact_matches": exact_matches,
        "partial_matches": partial_matches,
        "term_coverage": round(coverage_score, 4),
        "title_bonus": round(title_bonus, 4),
        "phrase_bonus": round(phrase_bonus, 4),
        "freq_bonus": round(freq_bonus, 4),
        "raw_score": round(raw_score, 4),
        "final_score": round(final_score, 4),
    }


def calculate_lexical_score(query: str, chunk: dict) -> float:
    """
    Sorgu ile chunk arasındaki sözcüksel uyumu açık formülle [0.0 - 1.0] hesaplar.
    
    Formül (Phase 3):
      Score = min(1.0, Coverage(0.65) + TitleBonus(0.15) + PhraseBonus(0.10) + FreqBonus(0.10))
    """
    return explain_lexical_score(query, chunk)["final_score"]


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
        Seçilen chunk'ları LLM için temiz, numaralı ve kaynak etiketli formata dönüştürür.
        rules.txt Adım 8 & 9: Şeffaf kaynak işaretleme ve gürültüsüz bağlam.
        """
        if not chunks:
            return ""

        blocks = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source_name", "belge")
            content = chunk.get("content", "").strip()
            # [Belge: ... | Konu: ...] başlığını kaldırıp saf içeriği alalım
            clean_content = re.sub(r"^\[Belge:[^\]]+\]\s*", "", content).strip()
            blocks.append(
                f"--- Kaynak {i} ({source}) ---\n{clean_content}"
            )

        return "\n\n".join(blocks)
