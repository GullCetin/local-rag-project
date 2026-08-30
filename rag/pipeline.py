"""
rag/pipeline.py — Kurumsal RAG Orkestrasyon Katmanı (rules.txt: Adım 8, 9, 10)
================================================================================
Bu modül, RAG yaşam döngüsünün tüm aşamalarını (Retrieval, Augment, Generate)
bir araya getirir ve izlenebilir (observable), şeffaf bir yanıt nesnesi döner.

Kurumsal RAG İlkeleri (rules.txt):
  - Adım 8: Hibrit retrieval ve takip sorusu çözümleme.
  - Adım 9: Kesin kaynak dayanaklı üretim ve ret garantisi.
  - Adım 10: Şeffaf izleme (latency, chunk sayısı, kaynak detayları).
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from config import TOP_K_CHUNKS
from rag.embedder import Embedder
from rag.generator import Generator, GROUNDED_REFUSAL_ANSWER
from rag.retriever import Retriever

logger = logging.getLogger(__name__)


def _extract_subject_from_history(chat_history: list[dict]) -> str:
    """
    Sohbet geçmişindeki en son anlamlı kullanıcı sorusunu veya konusunu çıkarır.
    """
    if not chat_history:
        return ""
    for msg in reversed(chat_history):
        if msg.get("role") == "user":
            content = msg.get("content", "").strip()
            if len(content) > 4:
                return content
    return ""


def _resolve_followup_query(question: str, chat_history: Optional[list[dict]]) -> str:
    """
    rules.txt Adım 8 & 10: Takip sorularını (followup) 0-ms gecikmeyle
    önceki konu bağlamıyla zenginleştirir. İlgisiz aramalara sapmayı %100 engeller.
    """
    if not chat_history or len(chat_history) == 0:
        return question

    q = question.strip()
    q_lower = q.lower()

    followup_triggers = [
        "bunu", "bunun", "bunlar", "bunları", "burada", "buradaki",
        "ondan", "onun", "onlar", "onları", "şunu", "şunun",
        "peki", "detaylandır", "açıkla", "örnek ver", "neden peki", "neden",
        "farkı ne", "farkları neler", "başka", "daha fazla", "devam et",
        "anlamı ne", "kimdir", "hangisi", "biraz daha", "ayrıntı", "daha detaylı"
    ]

    is_followup = (
        len(q.split()) <= 4 or
        any(trigger in q_lower for trigger in followup_triggers)
    )

    if not is_followup:
        return q

    prev_subject = _extract_subject_from_history(chat_history)
    if not prev_subject:
        return q

    # Soru ve bağlamı birleştirerek semantik arama sorgusu oluştur
    logger.info(f"Takip sorusu tespit edildi: '{q}' | Önceki Konu: '{prev_subject}'")
    return f"{prev_subject} {q}"


@dataclass
class RAGResponse:
    """
    Pipeline'ın döndürdüğü yapılandırılmış ve izlenebilir yanıt (rules.txt Adım 10).

    Fields:
        answer          : LLM'in ürettiği yanıt
        sources         : Kullanılan benzersiz kaynak belge adları
        chunks_used     : Kullanılan chunk sayısı
        top_chunks      : Ham chunk listesi (skorlar, alıntılar, debug için)
        retrieval_query : Gerçekleştirilen arama sorgusu
        latency_sec     : Toplam işlem süresi (saniye)
        error           : Hata mesajı (varsa)
    """
    answer: str
    sources: list[str] = field(default_factory=list)
    chunks_used: int = 0
    top_chunks: list[dict] = field(default_factory=list)
    retrieval_query: str = ""
    latency_sec: float = 0.0
    error: Optional[str] = None

    @property
    def has_error(self) -> bool:
        return self.error is not None

    @property
    def unique_sources(self) -> list[str]:
        """Tekrarsız ve sıralı kaynak belge listesi."""
        return sorted(set(self.sources))


class RAGPipeline:
    """
    Kurumsal standartlarda Yerel RAG Pipeline Sınıfı.
    """

    def __init__(self) -> None:
        self._embedder = Embedder()
        self._generator = Generator()
        self._retriever: Optional[Retriever] = None
        self._is_ready = False

    def load(self, model_alias: Optional[str] = None) -> None:
        """
        Embedding ve Chat modellerini yükler ve pipeline'ı hazır hale getirir.
        """
        if self._is_ready and model_alias is None:
            logger.debug("Pipeline zaten hazır.")
            return

        logger.info("=== RAG Pipeline Yükleniyor (rules.txt Standardı) ===")
        self._embedder.load()
        self._retriever = Retriever(self._embedder)
        self._generator.load(model_alias=model_alias)
        self._is_ready = True
        logger.info("=== RAG Pipeline Başarıyla Hazırlandı ===")

    def switch_llm_model(self, model_alias: str) -> None:
        """Pipeline çalışırken LLM modelini değiştirir."""
        logger.info(f"LLM model değiştiriliyor: {model_alias}")
        self._generator.load(model_alias=model_alias)
        logger.info(f"LLM model değiştirildi: {model_alias}")

    def ask(
        self,
        question: str,
        top_k: int = TOP_K_CHUNKS,
        chat_history: Optional[list[dict]] = None,
    ) -> RAGResponse:
        """
        Kullanıcının sorusunu rules.txt ilkelerine göre yanıtlar.
        """
        if not self._is_ready:
            raise RuntimeError(
                "Pipeline hazır değil. Önce pipeline.load() çağırın."
            )

        if not question or not question.strip():
            raise ValueError("Soru boş olamaz.")

        start_time = time.time()
        clean_question = question.strip()

        # 1. Takip sorusu tespiti ve hızlı bağlamsal sorgu çözümleme (Adım 8 & 10)
        search_query = _resolve_followup_query(clean_question, chat_history)
        logger.info(f"Arama sorgusu: '{search_query}' (Orijinal: '{clean_question}')")

        # 2. Retrieval (Adım 8)
        try:
            top_chunks = self._retriever.get_top_chunks(search_query, top_k=top_k)
        except Exception as e:
            logger.error(f"Retrieval hatası: {e}")
            elapsed = time.time() - start_time
            return RAGResponse(
                answer="Belgelerde arama yapılırken bir teknik hata oluştu.",
                retrieval_query=search_query,
                latency_sec=elapsed,
                error=str(e),
            )

        # Eşik altında kalınırsa veya DB boşsa: Kesin ret (Adım 0 & 9)
        if not top_chunks:
            elapsed = time.time() - start_time
            logger.info("Hiçbir ilgili chunk bulunamadı -> Standart ret cevabı dönülüyor.")
            return RAGResponse(
                answer=GROUNDED_REFUSAL_ANSWER,
                retrieval_query=search_query,
                latency_sec=elapsed,
                error=None,
            )

        # 3. XML Bağlam Formatlama (Adım 3 & 9)
        context = self._retriever.format_context(top_chunks)
        sources = list(dict.fromkeys([chunk["source_name"] for chunk in top_chunks]))

        # 4. Üretim (Adım 9)
        effective_question = clean_question
        if search_query != clean_question:
            effective_question = f"{clean_question} (Bağlam: {search_query})"

        try:
            answer = self._generator.generate(effective_question, context)
        except Exception as e:
            logger.error(f"Generation hatası: {e}")
            elapsed = time.time() - start_time
            return RAGResponse(
                answer="Cevap üretilirken bir model hatası oluştu.",
                sources=sources,
                chunks_used=len(top_chunks),
                top_chunks=top_chunks,
                retrieval_query=search_query,
                latency_sec=elapsed,
                error=str(e),
            )

        elapsed = time.time() - start_time
        logger.info(f"Cevap {elapsed:.2f} saniyede üretildi ({len(sources)} kaynak kullanıldı).")

        return RAGResponse(
            answer=answer,
            sources=sources,
            chunks_used=len(top_chunks),
            top_chunks=top_chunks,
            retrieval_query=search_query,
            latency_sec=elapsed,
        )

    @property
    def is_ready(self) -> bool:
        return self._is_ready
