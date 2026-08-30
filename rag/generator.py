"""
rag/generator.py — Kurumsal Düzeyde LLM Cevap Üretici (rules.txt: Adım 9)
===========================================================================
Bu modül, Foundry Local'daki chat modelini kullanarak kullanıcının
sorusuna YALNIZCA verilen bağlamı temel alan güvenilir, halüsinasyonsuz
ve hesap verebilir yanıtlar üretir.

Kurumsal RAG İlkeleri (rules.txt Adım 0 & Adım 9):
  - "Nazik yanlışlara" izin yok: Eksik/olmayan bilgi için uydurma yapılmaz.
  - Sıkı prompt sınırları: Model kendi genel bilgisini kullanamaz.
  - Kaynak ve dayanak işaretleme.
  - Anti-loop ve anti-think korumaları.
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

# Standart ret yanıtı (rules.txt Adım 0 & 9)
GROUNDED_REFUSAL_ANSWER = "Verilen belgelerde bu bilgi yer almamaktadır."


def _clean_response(text: str) -> str:
    """
    rules.txt Adım 9: Model çıktısını temizler ve güvenli hale getirir.
      1. <think> bloklarını ayıklar.
      2. Model promptu yankıladıysa (echo), asıl cevap bölümünü yakalar.
      3. Tekrarları ve XML etiketlerini temizle.
    """
    if not text:
        return ""

    # 0. Özel belirteçleri temizle
    cleaned = (
        text.replace("/no_think", "")
        .replace("<|im_start|>", "")
        .replace("<|im_end|>", "")
        .replace("<|endoftext|>", "")
    )

    # 1. <think>...</think> bloklarını temizle
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL)
    if "<think>" in cleaned and "</think>" not in cleaned:
        cleaned = re.sub(r"<think>.*", "", cleaned, flags=re.DOTALL)

    # 2. Eğer model satır başında prompt etiketlerini (Cevap:, Yanıt:, Asistan: vb.) yankıladıysa en son cevabı al
    # Cümle içinde geçen "güvenlik sorusu cevabı" gibi kelimeleri ASLA bölme!
    prompt_marker_re = re.compile(r"(?im)^\s*(?:cevap|yanıt|answer|response|asistan|assistant)\s*:\s*")
    marker_parts = prompt_marker_re.split(cleaned)
    if len(marker_parts) > 1:
        last_part = marker_parts[-1].strip()
        if len(last_part) > 15:
            cleaned = last_part

    # 3. Belge, Kaynak ve XML etiketlerini temizle
    cleaned = re.sub(r"\[Belge:[^\]]+\]", "", cleaned)
    cleaned = re.sub(r"---\s*Kaynak\s*\d+[^-\n]*---", "", cleaned)
    cleaned = re.sub(r"</?belge[^>]*>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</?source[^>]*>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</?doc[^>]*>", "", cleaned, flags=re.IGNORECASE)

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

    # 5. Cümle bazında n-gram döngü filtresi
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
    Streaming akışında sadece gerçekten ardışık 8-20 kelimelik uzun blok tekrarlarını yakalar.
    Kısa kelime benzerliklerinde asla kesme yapmaz.
    """
    tail = full_text[-500:]
    words = tail.split()
    n_words = len(words)
    if n_words < 16:
        return False, ""

    max_check = min(20, n_words // 2)
    for k in range(8, max_check + 1):
        unit_a = " ".join(words[-k:]).lower()
        unit_b = " ".join(words[-2 * k : -k]).lower()
        if unit_a == unit_b and len(unit_a) > 25:
            return True, unit_a
    return False, ""


def _call_with_timeout(fn, args=(), kwargs=None, timeout_sec: int = 120):
    """
    Fonksiyonu ayrı thread'de çalıştırıp timeout garantisi sağlar.
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
        raise TimeoutError(
            f"LLM yanıt süresi aşıldı ({timeout_sec}s). "
            "Model meşgul olabilir, lütfen tekrar deneyin."
        )

    if error_holder[0] is not None:
        raise error_holder[0]

    return result_holder[0]


class Generator:
    """
    Foundry Local Chat Modelini yöneten ve kurumsal güvenilirlik kurallarını uygulayan sınıf.
    """

    def __init__(self) -> None:
        self._model = None
        self._chat_client = None
        self._is_loaded = False
        self._current_alias: Optional[str] = None

    def load(self, model_alias: Optional[str] = None) -> None:
        """
        Chat modelini indirir ve RAM'e yükler.
        """
        target_alias = model_alias or LLM_MODEL_ALIAS

        if self._is_loaded and self._current_alias == target_alias:
            logger.debug("Chat modeli zaten yüklü.")
            return

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
        Hiperparametreleri uygular (temperature=0.1, penalties, max_tokens).
        """
        if self._chat_client and hasattr(self._chat_client, "settings") and self._chat_client.settings is not None:
            self._chat_client.settings.temperature = LLM_TEMPERATURE
            self._chat_client.settings.top_p = LLM_TOP_P
            self._chat_client.settings.max_tokens = LLM_MAX_TOKENS
            self._chat_client.settings.frequency_penalty = LLM_FREQUENCY_PENALTY
            self._chat_client.settings.presence_penalty = LLM_PRESENCE_PENALTY

    def rewrite_query(self, question: str, chat_history: list[dict]) -> str:
        """
        rules.txt Adım 8 & 9: Sohbet geçmişine bakarak takip sorusunu bağımsız arama sorgusuna çevirir.
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
            logger.warning(f"Sorgu yeniden yazma başarısız (orijinal sorgu kullanılıyor): {e}")

        return question

    def generate(self, question: str, context: str) -> str:
        """
        rules.txt Adım 9 İlkelerine Göre Güvenilir Cevap Üretir:
          - Sadece verilen bağlamdaki bilgileri kullanır.
          - complete_chat ile tek hamlede kararlı, tam ve hızlı yanıt alır.
          - Yanıt boş veya yetersizse GROUNDED_REFUSAL_ANSWER döner.
        """
        if not self._is_loaded:
            raise RuntimeError(
                "Chat modeli yüklenmemiş. Önce generator.load() çağırın."
            )

        MAX_CONTEXT_CHARS = 4500
        if len(context) > MAX_CONTEXT_CHARS:
            context = context[:MAX_CONTEXT_CHARS] + "\n...[bağlam optimize edildi]"
            logger.warning(f"Bağlam {MAX_CONTEXT_CHARS} karaktere optimize edildi.")

        user_message = (
            f"Aşağıdaki kaynak metne dayanarak '{question}' sorusunu Türkçe olarak detaylı, net ve eksiksiz yanıtla.\n\n"
            f"Kaynak Metin:\n{context}"
        )

        messages = [
            {"role": "system", "content": "Verilen kaynak metindeki bilgilere dayanarak soruları Türkçe olarak doğrudan ve eksiksiz yanıtlayan profesyonel bir asistansın. Metinde yer almayan dış bilgileri ekleme."},
            {"role": "user",   "content": user_message},
        ]

        last_error: Exception = None
        for attempt in range(2):
            try:
                logger.info(f"LLM çağrısı yapılıyor (deneme {attempt + 1}/2)...")
                self._apply_generation_settings()

                # complete_chat ile doğrudan, kesintisiz yanıt
                res = _call_with_timeout(
                    self._chat_client.complete_chat,
                    args=(messages,),
                    timeout_sec=90,
                )
                raw_answer = res.choices[0].message.content if res.choices else ""
                clean_answer = _clean_response(raw_answer)

                if clean_answer and len(clean_answer.strip()) >= 5:
                    logger.info("LLM yanıtı başarıyla üretildi.")
                    return clean_answer

                # Boş döndüyse streaming ile dene
                logger.info("complete_chat kısa döndü, streaming deneniyor...")
                full_stream = ""
                for chunk in self._chat_client.complete_streaming_chat(messages):
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            full_stream += delta.content

                clean_answer = _clean_response(full_stream)
                if clean_answer and len(clean_answer.strip()) >= 5:
                    return clean_answer

                return GROUNDED_REFUSAL_ANSWER

            except TimeoutError as e:
                last_error = e
                logger.warning(f"Deneme {attempt + 1}/2 zaman aşımı: {e}")

            except Exception as e:
                last_error = e
                logger.warning(f"Deneme {attempt + 1}/2 başarısız: {e}")
                if attempt < 1:
                    time.sleep(1)

        logger.error(f"LLM üretimi başarısız: {last_error}")
        raise RuntimeError(
            f"Model yanıt üretemedi. Son hata: {last_error}"
        ) from last_error

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded
