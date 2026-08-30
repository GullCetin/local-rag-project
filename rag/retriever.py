"""
rag/retriever.py — Cosine Similarity Tabanlı Chunk Retrieval
=============================================================
Bu modül, kullanıcının sorgusunu embed eder ve SQLite veritabanındaki
chunk'lar arasında en ilgili olanları cosine similarity ile bulur.

Neden cosine similarity?
  Vektörlerin büyüklüğünden bağımsız olarak yön benzerliğini ölçer.
  Kısa ve uzun metinlerin adil karşılaştırılmasını sağlar.
  Embedding modelleri bu metrik için optimize edilmiştir.

Ölçeklenebilirlik notu:
  Bu implementasyon tüm vektörleri belleğe alarak karşılaştırır.
  Küçük veri setleri (< 1000 chunk) için uygundur.
  Daha büyük setlerde Chroma, FAISS veya Qdrant kullanılabilir.
"""

import logging
from typing import Optional

import numpy as np

from config import SCORE_THRESHOLD, TOP_K_CHUNKS
from db.manager import get_all_chunks
from rag.embedder import Embedder

import re

logger = logging.getLogger(__name__)


def calculate_lexical_score(query: str, chunk: dict) -> float:
    """
    Sorgu ile chunk arasındaki sözcük, başlık ve dosya adı uyumunu hesaplar [0.0 - 1.0].
    
    Bu fonksiyon, saf semantik aramada (dense vector) gözden kaçabilen
    kesin başlık ve kavram eşleşmelerini (örn. 'Python Programlama Dili')
    öne çıkararak gürültüyü (noise) eler.
    """
    words = re.findall(r"\w+", query.lower())
    stop_words = {
        "nedir", "nelerdir", "nasıl", "ve", "ile", "bir", "mi", "mı",
        "mu", "mü", "bu", "şu", "hakkında", "için", "ne", "var", "yok"
    }
    keywords = [w for w in words if w not in stop_words and len(w) > 1]
    if not keywords:
        return 0.0

    content_lower = chunk["content"].lower()
    source_lower = chunk["source_name"].lower()

    score = 0.0
    for kw in keywords:
        # 1. Dosya adında geçiyorsa çok güçlü sinyal
        if kw in source_lower:
            score += 0.35
        # 2. Başlıkta ([Konu: ...] veya [Belge: ...]) geçiyorsa çok güçlü sinyal
        first_line = content_lower.split("\n")[0] if "\n" in content_lower else content_lower
        if kw in first_line:
            score += 0.35
        # 3. Metin içi frekans
        count = content_lower.count(kw)
        if count > 0:
            score += min(0.3, count * 0.1)

    return min(1.0, score)


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    İki vektör arasındaki cosine similarity değerini hesaplar.
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
    SQLite'taki chunk'lar üzerinde Hibrit Arama (Dense Vector + Lexical) yapan sınıf.
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
        """
        if not query or not query.strip():
            raise ValueError("Sorgu boş olamaz.")

        clean_query = query.strip()

        # 1. Sorguyu embed et
        query_vector = self._embedder.embed(clean_query)

        # 2. DB'den tüm chunk'ları al
        all_chunks = get_all_chunks()

        if not all_chunks:
            logger.warning("Veritabanı boş. Önce 'python ingest.py' çalıştırın.")
            return []

        # 3. Hibrit skor hesapla (0.6 Dense + 0.4 Lexical)
        scored = []
        for chunk in all_chunks:
            dense_score = cosine_similarity(query_vector, chunk["embedding"])
            lexical_score = calculate_lexical_score(clean_query, chunk)
            hybrid_score = 0.60 * dense_score + 0.40 * lexical_score

            scored.append({
                "id": chunk["id"],
                "source_name": chunk["source_name"],
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "score": hybrid_score,
                "dense_score": dense_score,
                "lexical_score": lexical_score,
            })

        # 4. Hibrit skora göre sırala
        scored.sort(key=lambda x: x["score"], reverse=True)

        # Düşük benzerlik skorlu chunk'ları ele
        filtered = [c for c in scored if c["score"] >= SCORE_THRESHOLD]

        if not filtered:
            logger.warning(
                f"Hiçbir chunk SCORE_THRESHOLD ({SCORE_THRESHOLD}) eşiğini geçemedi. "
                f"En yüksek skor: {scored[0]['score']:.4f}"
            )
            return []

        top_chunks = filtered[:top_k]

        logger.debug(
            f"Top-{top_k} chunk bulundu. "
            f"En yüksek skor: {top_chunks[0]['score']:.4f} "
            f"({top_chunks[0]['source_name']})"
        )

        return top_chunks

    def format_context(self, chunks: list[dict]) -> str:
        """
        Chunk listesini LLM'e verilecek bağlam string'ine dönüştürür.

        Modelin skorları, teknik metinleri veya başlıkları kopyalamasını engellemek için
        temiz <belge kaynak="...">...</belge> yapısı kullanılır.
        """
        if not chunks:
            return "İlgili belge alıntısı bulunamadı."

        parts = []
        for chunk in chunks:
            raw_content = chunk["content"]
            # Başlıkların papağan gibi tekrarlanmasını önlemek için satır başı # başlıklarını temizle
            clean_content = re.sub(r"^#+\s*.*$", "", raw_content, flags=re.MULTILINE).strip()
            if not clean_content:
                clean_content = raw_content.strip()

            parts.append(
                f'<belge kaynak="{chunk["source_name"]}">\n'
                f'{clean_content}\n'
                f'</belge>'
            )

        return "\n\n".join(parts)
