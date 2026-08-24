"""
rag/generator.py — LLM Cevap Üretici
======================================
Bu modül, Foundry Local'daki chat modelini kullanarak
kullanıcının sorusuna kaynak destekli yanıt üretir.

Temel tasarım kararı:
  LLM sadece verilen bağlamı kullanmalı, dışarıdan bilgi eklememelidir.
  Bu "grounded generation" yaklaşımı halüsinasyonu minimize eder.
  Sistem promptu bu kısıtlamayı net şekilde belirtir.
"""

import logging
from typing import Optional

from foundry_local_sdk import Configuration, FoundryLocalManager

from config import APP_NAME, LLM_MODEL_ALIAS, QUERY_REWRITE_PROMPT, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class Generator:
    """
    Foundry Local chat modelini yöneten sınıf.
    """

    def __init__(self) -> None:
        self._model = None
        self._chat_client = None
        self._is_loaded = False

    def load(self) -> None:
        """
        Chat modelini indirir (gerekirse) ve RAM'e yükler.
        """
        if self._is_loaded:
            logger.debug("Chat modeli zaten yüklü.")
            return

        try:
            manager = FoundryLocalManager.instance
        except Exception:
            pass

        try:
            logger.info("FoundryLocalManager başlatılıyor (generator)...")
            config = Configuration(app_name=APP_NAME)
            FoundryLocalManager.initialize(config)
        except Exception:
            logger.debug("FoundryLocalManager zaten başlatılmış, devam ediliyor.")

        manager = FoundryLocalManager.instance

        logger.info(f"Chat modeli aranıyor: '{LLM_MODEL_ALIAS}'")
        self._model = manager.catalog.get_model(LLM_MODEL_ALIAS)

        if self._model is None:
            raise RuntimeError(
                f"Chat modeli '{LLM_MODEL_ALIAS}' katalogda bulunamadı. "
                f"Lütfen config.py'yi kontrol edin."
            )

        if not self._model.is_cached:
            logger.info("Chat modeli indiriliyor...")
            def _progress(p: float) -> None:
                print(f"\r  İndiriliyor: %{round(p)}", end="", flush=True)
            self._model.download(_progress)
            print()

        logger.info("Chat modeli RAM'e yükleniyor...")
        self._model.load()
        self._chat_client = self._model.get_chat_client()
        self._is_loaded = True
        logger.info("Chat modeli hazır.")

    def rewrite_query(self, question: str, chat_history: list[dict]) -> str:
        """
        Sohbet geçmişine bakarak kullanıcının takip sorusunu
        (örn. 'detaylandır', 'bunu açıkla') bağımsız bir arama sorgusuna çevirir.
        """
        if not chat_history or len(chat_history) == 0:
            return question

        # Son 4 mesajı özetle
        recent_history = chat_history[-4:]
        history_lines = []
        for msg in recent_history:
            role = "Kullanıcı" if msg.get("role") == "user" else "Asistan"
            # Asistan mesajını kısa tut
            content = msg.get("content", "")[:150]
            history_lines.append(f"{role}: {content}")

        history_text = "\n".join(history_lines)
        user_prompt = (
            f"SOHBET GEÇMİŞİ:\n{history_text}\n\n"
            f"KULLANICININ YENİ SORUSU: {question}\n\n"
            f"BAĞIMSIZ ARAMA SORGUSU:"
        )

        try:
            response = self._chat_client.complete_chat([
                {"role": "system", "content": QUERY_REWRITE_PROMPT},
                {"role": "user", "content": user_prompt},
            ])
            rewritten = response.choices[0].message.content.strip().strip('"').strip("'")
            if rewritten and len(rewritten) > 3 and not rewritten.startswith("Hata"):
                logger.info(f"Sorgu yeniden yazıldı: '{question}' → '{rewritten}'")
                return rewritten
        except Exception as e:
            logger.warning(f"Sorgu yeniden yazma hatası: {e}")

        return question

    def generate(self, question: str, context: str) -> str:
        """
        Kullanıcının sorusunu ve bağlamı kullanarak LLM'den cevap üretir.
        """
        if not self._is_loaded:
            raise RuntimeError(
                "Chat modeli yüklenmemiş. Önce generator.load() çağırın."
            )

        user_message = (
            f"BELGE ALINTILARI:\n"
            f"{context}\n\n"
            f"SORU: {question}"
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ]

        try:
            response = self._chat_client.complete_chat(messages)
            answer = response.choices[0].message.content
            return answer.strip()
        except Exception as e:
            logger.error(f"LLM cevap üretme hatası: {e}")
            raise RuntimeError(f"Model yanıt üretemedi: {e}") from e

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded
