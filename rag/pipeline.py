"""
rag/pipeline.py — RAG Orkestrasyon Katmanı
===========================================
Bu modül, RAG pipeline'ının tüm bileşenlerini bir araya getirir.

Pipeline akışı:
  Kullanıcı sorusu
      ↓
  [Embedder] → Sorgu vektörü
      ↓
  [Retriever] → En ilgili Top-K chunk
      ↓
  [Generator] → System prompt + bağlam + soru → LLM → Cevap
      ↓
  Cevap + Kaynaklar

Bu modül UI katmanının (CLI veya Streamlit) doğrudan kullandığı
tek giriş noktasıdır.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from config import TOP_K_CHUNKS
from rag.embedder import Embedder
from rag.generator import Generator
from rag.retriever import Retriever

logger = logging.getLogger(__name__)


def _is_followup_question(question: str) -> bool:
    """
    Kullanıcı sorusunun önceki konuşmaya referans veren bir takip sorusu
    olup olmadığını tespit eder. Bağımsız sorularda gereksiz LLM çağrısını önler.
    """
    q = question.strip().lower()
    followup_triggers = [
        "bunu", "bunun", "bunlar", "bunları", "burada", "buradaki",
        "ondan", "onun", "onlar", "onları", "şunu", "şunun",
        "peki", "detaylandır", "açıkla", "örnek ver", "neden peki",
        "farkı ne", "farkları neler", "başka", "daha fazla", "devam et"
    ]
    return any(trigger in q for trigger in followup_triggers)


@dataclass
class RAGResponse:
    """
    Pipeline'ın döndürdüğü yapılandırılmış yanıt.

    Fields:
        answer       : LLM'in ürettiği yanıt
        sources      : Kullanılan kaynak belge adları (tekrarsız)
        chunks_used  : Kullanılan chunk sayısı
        top_chunks   : Ham chunk listesi (debug/UI için)
        error        : Hata mesajı (varsa)
    """
    answer: str
    sources: list[str] = field(default_factory=list)
    chunks_used: int = 0
    top_chunks: list[dict] = field(default_factory=list)
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
    Local RAG uygulamasının ana pipeline sınıfı.

    Kullanım:
      pipeline = RAGPipeline()
      pipeline.load()  # Başlangıçta bir kez

      response = pipeline.ask("Python nedir?")
      print(response.answer)
      print(response.unique_sources)
    """

    def __init__(self) -> None:
        self._embedder = Embedder()
        self._generator = Generator()
        self._retriever: Optional[Retriever] = None
        self._is_ready = False

    def load(self, model_alias: Optional[str] = None) -> None:
        """
        Tüm modelleri yükler ve pipeline'ı hazır hale getirir.
        Bu işlem birkaç dakika sürebilir (özellikle ilk çalıştırmada).

        Yükleme sırası:
          1. Embedding modeli (küçük, hızlı)
          2. Chat modeli (büyük, yavaş)
          3. Retriever oluştur
        """
        if self._is_ready and model_alias is None:
            logger.debug("Pipeline zaten hazır.")
            return

        logger.info("=== RAG Pipeline Yükleniyor ===")

        # Embedding modelini yükle
        self._embedder.load()

        # Retriever'ı oluştur (embedder gerekli)
        self._retriever = Retriever(self._embedder)

        # Chat modelini yükle
        self._generator.load(model_alias=model_alias)

        self._is_ready = True
        logger.info("=== RAG Pipeline Hazır ===")

    def switch_llm_model(self, model_alias: str) -> None:
        """
        Hali hazırda çalışan pipeline'da LLM modelini değiştirir.
        Embedding modeli ve retriever değişmez.
        """
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
        Kullanıcının sorusunu RAG pipeline'ından geçirir.

        Conversational RAG Akışı:
          1. Sohbet geçmişi varsa takip sorusunu bağımsız arama sorgusuna çevir
          2. Arama sorgusuyla ilgili belge parçalarını getir
          3. Belge parçaları + soru ile yanıt üret
        """
        if not self._is_ready:
            raise RuntimeError(
                "Pipeline hazır değil. Önce pipeline.load() çağırın."
            )

        if not question or not question.strip():
            raise ValueError("Soru boş olamaz.")

        clean_question = question.strip()

        # 1. Takip sorusu tespiti ve sorgu yeniden yazımı
        search_query = clean_question
        if chat_history and len(chat_history) > 0 and _is_followup_question(clean_question):
            search_query = self._generator.rewrite_query(clean_question, chat_history)

        logger.info(f"Arama sorgusu: '{search_query}'")

        # 2. Retrieval
        try:
            top_chunks = self._retriever.get_top_chunks(search_query, top_k=top_k)
        except Exception as e:
            logger.error(f"Retrieval hatası: {e}")
            return RAGResponse(
                answer="Belgelerde arama yapılırken bir hata oluştu.",
                error=str(e),
            )

        # DB boşsa
        if not top_chunks:
            return RAGResponse(
                answer="Verilen belgelerde bu soruya yanıt verebilecek yeterli bilgi bulunmamaktadır.",
                error=None,
            )

        # 2. Bağlamı hazırla
        context = self._retriever.format_context(top_chunks)
        sources = list(dict.fromkeys([chunk["source_name"] for chunk in top_chunks]))

        logger.info(
            f"Retrieval tamamlandı: {len(top_chunks)} chunk, "
            f"kaynaklar: {sources}"
        )

        # 3. Cevap üret
        # Takip sorusu ise çözümlenmiş arama konusunu da soruya bağla
        effective_question = clean_question
        if search_query != clean_question:
            effective_question = f"{clean_question} (Konu: {search_query})"

        try:
            answer = self._generator.generate(effective_question, context)
        except Exception as e:
            logger.error(f"Generation hatası: {e}")
            return RAGResponse(
                answer="Cevap üretilirken bir hata oluştu.",
                sources=sources,
                chunks_used=len(top_chunks),
                top_chunks=top_chunks,
                error=str(e),
            )

        logger.info("Cevap üretildi.")

        return RAGResponse(
            answer=answer,
            sources=sources,
            chunks_used=len(top_chunks),
            top_chunks=top_chunks,
        )

    @property
    def is_ready(self) -> bool:
        return self._is_ready
