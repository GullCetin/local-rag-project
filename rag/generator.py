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
import re
import time
import threading
from typing import Optional

from foundry_local_sdk import Configuration, FoundryLocalManager

from config import (
    APP_NAME,
    LLM_FREQUENCY_PENALTY,
    LLM_MAX_TOKENS,
    LLM_MODEL_ALIAS,
    LLM_PRESENCE_PENALTY,
    LLM_TEMPERATURE,
    LLM_TOP_P,
    QUERY_REWRITE_PROMPT,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


def _clean_response(text: str) -> str:
    """
    1. Qwen3 / DeepSeek gibi modellerin <think>...</think> düşünme bloklarını temizler.
    2. Modelin sızdırabileceği prompt metinlerini (GÖREV, KURALLAR, SORU, CEVAP vb.) ayıklar.
    3. Ham XML/HTML etiketlerini (<belge>, </belge> vb.) ayıklar.
    4. Ardışık cümle/satır tekrarlarını (degeneration loop) önler.
    """
    if not text:
        return ""
    # 1. Düşünme bloklarını temizle
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    if "<think>" in cleaned and "</think>" not in cleaned:
        cleaned = re.sub(r"<think>.*", "", cleaned, flags=re.DOTALL)

    # 2. Eğer model prompt sonundaki 'CEVAP:' veya 'Cevap:' etiketini kopyaladıysa, o etiketten önceki tüm prompt metnini at
    for marker in ["CEVAP:", "Cevap:", "YANIT:", "Yanıt:", "Cevabınız:", "Answer:", "RESPONSE:"]:
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[-1]

    # 3. Prompt başlıkları ve kuralları sızdıysa satırları temizle
    cleaned = re.sub(r"^(GöREV|GÖREV|KURALLAR|KAYNAK BELGELER|KAYNAKLAR|SORU|KULLANICI SORUSU|BELGE ALINTILARI|LÜTFEN):?.*$", "", cleaned, flags=re.MULTILINE | re.IGNORECASE)
    cleaned = re.sub(r"</?belge[^>]*>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</?source[^>]*>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^---+.*$", "", cleaned, flags=re.MULTILINE)

    # 4. Ardışık tekrar eden satırları temizle
    lines = cleaned.split("\n")
    deduped_lines = []
    prev_line = None
    for line in lines:
        stripped = line.strip()
        if stripped and stripped == prev_line:
            continue
        prev_line = stripped
        deduped_lines.append(line)

    cleaned_result = "\n".join(deduped_lines).strip()
    cleaned_result = re.sub(r"[<]+$", "", cleaned_result).strip()

    # 5. Cümle bazında döngü filtresi
    sentences = re.split(r"(?<=[.!?\n])\s+", cleaned_result)
    seen_counts = {}
    valid_sentences = []
    for s in sentences:
        s_clean = s.strip().lower()
        if len(s_clean) > 8:
            count = seen_counts.get(s_clean, 0) + 1
            seen_counts[s_clean] = count
            if count > 2:
                continue
        valid_sentences.append(s)

    final_result = " ".join(valid_sentences).strip()
    return re.sub(r"[<]+$", "", final_result).strip()


def _detect_repetition_loop(full_text: str) -> tuple[bool, str]:
    """
    Metin akışında ardışık tekrar eden 2 ila 12 kelimelik n-gram döngülerini yakalar.
    Döngü bulunursa (True, tekrarlanan_metin) döner.
    """
    tail = full_text[-250:]
    words = tail.split()
    n_words = len(words)
    if n_words < 6:
        return False, ""

    max_check = min(12, n_words // 2)
    for k in range(2, max_check + 1):
        unit_a = " ".join(words[-k:]).lower()
        unit_b = " ".join(words[-2 * k : -k]).lower()
        if unit_a == unit_b and len(unit_a) > 5:
            return True, unit_a
    return False, ""


def _call_with_timeout(fn, args=(), kwargs=None, timeout_sec: int = 90):
    """
    Verilen fonksiyonu ayrı bir thread'de çalıştırır, timeout_sec süresinde
    sonuç alınmazsa TimeoutError fırlatır.
    complete_chat() parametresinde timeout desteklemediği için
    bu wrapper kullanılır.
    """
    if kwargs is None:
        kwargs = {}

    result_holder = [None]
    error_holder  = [None]

    def _worker():
        try:
            result_holder[0] = fn(*args, **kwargs)
        except Exception as exc:
            error_holder[0] = exc

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=timeout_sec)

    if t.is_alive():
        # Thread hâlâ çalışıyorsa: zaman aşımı
        raise TimeoutError(
            f"LLM yanıt süresi aşıldı ({timeout_sec}s). "
            "Model meşgul olabilir, lütfen tekrar deneyin."
        )

    if error_holder[0] is not None:
        raise error_holder[0]

    return result_holder[0]


class Generator:
    """
    Foundry Local chat modelini yöneten sınıf.
    """

    def __init__(self) -> None:
        self._model = None
        self._chat_client = None
        self._is_loaded = False
        self._current_alias: Optional[str] = None

    def load(self, model_alias: Optional[str] = None) -> None:
        """
        Chat modelini indirir (gerekirse) ve RAM'e yükler.
        model_alias verilirse o modeli kullanır, verilmezse config.py'den alır.
        """
        target_alias = model_alias or LLM_MODEL_ALIAS

        # Aynı model zaten yüklendi mi?
        if self._is_loaded and self._current_alias == target_alias:
            logger.debug("Chat modeli zaten yüklü.")
            return

        # Farklı model isteniyorsa öncekini kaldır
        if self._is_loaded and self._current_alias != target_alias:
            logger.info(f"Model değiştiriliyor: {self._current_alias} → {target_alias}")
            try:
                self._model.unload()
            except Exception:
                pass
            self._is_loaded = False
            self._model = None
            self._chat_client = None

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

        logger.info(f"Chat modeli aranıyor: '{target_alias}'")
        self._model = manager.catalog.get_model(target_alias)

        if self._model is None:
            raise RuntimeError(
                f"Chat modeli '{target_alias}' katalogda bulunamadı. "
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
        self._apply_generation_settings()
        self._current_alias = target_alias
        self._is_loaded = True
        logger.info(f"Chat modeli hazır: {target_alias}")

    def _apply_generation_settings(self) -> None:
        """
        Chat client'a hiperparametreleri (temperature, penalties, max_tokens) uygular.
        Tekrarları (degeneration loop) önler ve kaliteli yanıt üretimini sağlar.
        """
        if self._chat_client and hasattr(self._chat_client, "settings") and self._chat_client.settings is not None:
            self._chat_client.settings.temperature = LLM_TEMPERATURE
            self._chat_client.settings.top_p = LLM_TOP_P
            self._chat_client.settings.max_tokens = LLM_MAX_TOKENS
            self._chat_client.settings.frequency_penalty = LLM_FREQUENCY_PENALTY
            self._chat_client.settings.presence_penalty = LLM_PRESENCE_PENALTY

    def rewrite_query(self, question: str, chat_history: list[dict]) -> str:
        """
        Sohbet geçmişine bakarak kullanıcının takip sorusunu
        (örn. 'detaylandır', 'bunu açıkla') bağımsız bir arama sorgusuna çevirir.
        """
        if not chat_history or len(chat_history) == 0:
            return question

        recent_history = chat_history[-4:]
        history_lines = []
        for msg in recent_history:
            role = "Kullanıcı" if msg.get("role") == "user" else "Asistan"
            content = msg.get("content", "")[:150]
            history_lines.append(f"{role}: {content}")

        history_text = "\n".join(history_lines)
        user_prompt = (
            f"SOHBET GEÇMİŞİ:\n{history_text}\n\n"
            f"KULLANICININ YENİ SORUSU: {question}\n\n"
            f"BAĞIMSIZ ARAMA SORGUSU:"
        )

        messages = [
            {"role": "system", "content": QUERY_REWRITE_PROMPT},
            {"role": "user",   "content": user_prompt},
        ]

        try:
            self._apply_generation_settings()
            response = _call_with_timeout(
                self._chat_client.complete_chat,
                args=(messages,),
                timeout_sec=30,
            )
            raw = response.choices[0].message.content
            rewritten = _clean_response(raw).strip('"').strip("'")
            if rewritten and len(rewritten) > 3 and not rewritten.startswith("Hata"):
                logger.info(f"Sorgu yeniden yazıldı: '{question}' → '{rewritten}'")
                return rewritten
        except Exception as e:
            logger.warning(f"Sorgu yeniden yazma başarısız (geçici): {e}")

        return question

    def generate(self, question: str, context: str) -> str:
        """
        Kullanıcının sorusunu ve bağlamı kullanarak LLM'den cevap üretir.

        - Streaming üzerinden token bazlı üretir ve olası döngüsel tekrarları anında keser.
        - Bağlam otomatik olarak token limitine göre optimize edilir.
        - 120 saniyelik güvenli zaman aşımı.
        """
        if not self._is_loaded:
            raise RuntimeError(
                "Chat modeli yüklenmemiş. Önce generator.load() çağırın."
            )

        # Bağlam uzunluğu güvenliği
        MAX_CONTEXT_CHARS = 4000
        if len(context) > MAX_CONTEXT_CHARS:
            context = context[:MAX_CONTEXT_CHARS] + "\n...[bağlam kısaltıldı]"
            logger.warning(f"Bağlam {MAX_CONTEXT_CHARS} karaktere kısaltıldı.")

        user_message = (
            f"KAYNAK BELGELER:\n"
            f"----------------------------------------\n"
            f"{context}\n"
            f"----------------------------------------\n\n"
            f"SORU: {question}\n\n"
            f"CEVAP:"
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ]

        def _do_stream_generation() -> str:
            self._apply_generation_settings()
            full_text = ""
            for chunk in self._chat_client.complete_streaming_chat(messages):
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        full_text += delta.content

                        # Multi-gram loop detector (2 ila 12 kelimelik döngüleri anında kes)
                        has_loop, loop_text = _detect_repetition_loop(full_text)
                        if has_loop:
                            logger.info(f"Döngü tespit edildi ve kesildi: '{loop_text}'")
                            full_text = full_text[: -len(loop_text)].strip()
                            break
            return full_text

        last_error: Exception = None
        for attempt in range(2):
            try:
                logger.info(f"LLM çağrısı yapılıyor (deneme {attempt + 1}/2)...")
                raw_answer = _call_with_timeout(_do_stream_generation, timeout_sec=120)
                clean_answer = _clean_response(raw_answer)
                if not clean_answer:
                    # Model boş cevap verdiyse complete_chat yedek çağrısı yap
                    logger.info("Streaming boş döndü, complete_chat deneniyor...")
                    res = _call_with_timeout(
                        self._chat_client.complete_chat,
                        args=(messages,),
                        timeout_sec=60,
                    )
                    clean_answer = _clean_response(res.choices[0].message.content)

                logger.info("LLM yanıtı başarıyla üretildi.")
                return clean_answer

            except TimeoutError as e:
                last_error = e
                logger.warning(f"Deneme {attempt + 1}/2 zaman aşımı: {e}")

            except Exception as e:
                last_error = e
                logger.warning(f"Deneme {attempt + 1}/2 başarısız: {e}")
                if attempt < 1:
                    time.sleep(2)

        logger.error(f"LLM üretimi başarısız: {last_error}")
        raise RuntimeError(
            f"Model yanıt üretemedi. Son hata: {last_error}"
        ) from last_error

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded
