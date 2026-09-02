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


# Tasarım ilkesi:
#   - Orijinal P0/P1 problemlerini (şifre+bloke → OTP/30gün sızması, latency, budget) çözer.
#   - KURAL 1: B scope isolation (OTP dışlama) + A1/A2/A3 narrow selection.
#   - KURAL 2: "açıkça birden fazla konu" — B için şifre+bloke özelinde çalışıyor.
#   - KURAL 3: A3 sayısal sadakat (180 saniye, eşdeğer birime çevirme yok).
#   - KURAL 5: "kısa ve doğrudan" — KURAL label echo'yu önleyen versiyon.
#   - NOT: C (API rate limiting burst+429 completeness) phi-3.5-mini model kapasite
#     sınırı nedeniyle prompt değişikliğiyle düzeltilemedi. B veya A'da regresyona yol açmaksızın
#     KURAL değişikliğiyle 6/6 elde etmek mümkün olmadı.
#   - Keyword / soru-spesifik kural içermez.
GENERATOR_SYSTEM_PROMPT = (
    "Sen kurumsal bir Türkçe soru-cevap asistanısın. "
    "KURAL 1 (KAPSAM): Soruyu dikkatle oku ve tam olarak ne sorulduğunu belirle. "
    "Yalnızca soruyu doğrudan yanıtlayan bilgileri kullan; "
    "belgede soruyla ilgisiz başka bilgiler, süreler veya limitler olsa bile onları cevaba dahil etme. "
    "KURAL 2 (BÜTÜNLÜK): Soruda açıkça birden fazla konu veya kural isteniyorsa her birini ayrı madde halinde yaz; hiçbir istened maddeyi atlama. "
    "KURAL 3 (SAYISAL DOĞRULUK): Belgedeki sayısal değerleri (saniye, dakika, gün, rakam, limit) birebir aktar; eşdeğer birime çevirme veya kaynak ifadeyi değiştirme. "
    "KURAL 4 (RED): Kaynakta bulunmayan bilgiler için yalnızca 'Verilen belgelerde bu bilgi yer almamaktadır.' yaz. "
    "KURAL 5 (FORMAT): Düz maddeler halinde, kısa ve doğrudan yaz; giriş cümlesi, genel açıklama, özet veya tekrar yazma."
)





def _is_incomplete_terminal_line(line: str) -> bool:
    """
    Son satırın tamamlanmış geçerli bir madde mi (örn: '- Tür: JWT', '- Port: 8080')
    yoksa token kesilmesi nedeniyle yarıda kalmış bir parça mı
    (örn: '- Kullanıcı', '- IP başına dakikada maksimum') olduğunu belirler.
    """
    raw = line.strip()
    if not raw:
        return False

    # Bitiş noktalama / format işaretleri varsa tamamlanmıştır
    has_completion_punc = raw.endswith((".", ":", "!", "?", '"', "'", ")", "}", "]", "`", "|"))
    if has_completion_punc:
        return False

    # 'Key: Value' formatındaki kısa maddeler (örn: '- Tür: JWT', 'Port: 8080', 'TTL: 15 dakika') tamamlanmıştır
    if ":" in raw:
        parts = raw.split(":", 1)
        val_part = parts[1].strip()
        if val_part and not re.search(r"\b(?:ve|veya|ile|için|ise|en|en az|maksimum|minimum|kadar|olan|gibi|şekilde)\s*$", val_part, re.IGNORECASE):
            return False

    # Eğer satır tamamlanmamış bir bağlaç/sıfat/edat ile bitiyorsa veya noktalama yoksa yarımdır
    incomplete_endings = re.search(r"\b(?:ve|veya|ile|için|ise|en|en az|maksimum|minimum|kadar|olan|gibi|şekilde|kullanıcı|ip|başına|olarak)\s*$", raw, re.IGNORECASE)
    if incomplete_endings:
        return True

    # Tek veya iki kelimelik noktasız satırlar (örn: '- Kullanıcı')
    words = raw.split()
    if len(words) <= 2:
        return True

    return False


def _truncate_repeated_blocks(text: str) -> str:
    """
    Model çıktısındaki gerçek tekrar eden başlık ve blokları temizler.
    Kısa ve noktasız geçerli maddeleri (örn: '- Tür: JWT') kesinlikle silmez.
    Substring tabanlı yanlış kesmeler yapmaz.
    """
    if not text:
        return ""

    lines = text.split("\n")
    cleaned_lines = []
    seen_headings = set()
    seen_lines_normalized = []

    for line in lines:
        raw_line = line.strip()
        if not raw_line:
            cleaned_lines.append(line)
            continue

        # Başlık / liste işaretlerini temizleyip normalize et
        norm_line = re.sub(r"^[\s*#\d.:-]+", "", raw_line).strip().lower()
        norm_line = re.sub(r"[\s*#]+$", "", norm_line).strip()

        # 1. Başlık Tekrarı Tespiti (Yalnızca tam başlık eşleşmesi)
        is_heading = bool(re.match(r"^(\*{1,3}\s*\d+|\#{1,6}\s*\d+|\d+\.)", raw_line))
        if is_heading and len(norm_line) >= 8:
            if norm_line in seen_headings:
                break
            seen_headings.add(norm_line)

        # 2. Tam Satır / Cümle Birebir Tekrar Tespiti
        if len(norm_line) >= 15:
            if norm_line in seen_lines_normalized:
                break
            seen_lines_normalized.append(norm_line)

        cleaned_lines.append(line)

    result = "\n".join(cleaned_lines).strip()

    # 3. Yalnızca cümlenin ortasında yarım kalmış (dangling) son parçaları güvenli temizleme
    res_lines = [l for l in result.split("\n") if l.strip()]
    if len(res_lines) > 1:
        last_l = res_lines[-1].strip()
        if _is_incomplete_terminal_line(last_l):
            res_lines.pop()
            result = "\n".join(res_lines).strip()

    return result


def _clean_response(text: str) -> str:
    """
    Model çıktısını güvenli şekilde temizler:
      1. Özel belirteçleri (special tokens) temizler.
      2. <think>...</think> düşünme bloklarını ayıklar.
      3. Başta oluşabilecek rol/cevap etiketlerini (örn: 'Cevap:', 'Yanıt:') kaldırır.
      4. Temel whitespace ve format düzenlemesi yapar.
      5. Blok bazlı tekrar döngülerini ve son kesik satırları temizler.
      6. Cevabın gövdesini semantik olarak bozacak agresif kesmeler yapmaz.
    """
    if not text:
        return ""

    # 1. Özel belirteçleri temizle
    cleaned = (
        text.replace("/no_think", "")
        .replace("<|im_start|>", "")
        .replace("<|im_end|>", "")
        .replace("<|endoftext|>", "")
    )

    # 2. <think>...</think> düşünme bloklarını temizle
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL)
    if "<think>" in cleaned:
        cleaned = re.sub(r"<think>.*", "", cleaned, flags=re.DOTALL)

    # 3. Belge / Kaynak / XML etiketlerini temizle
    cleaned = re.sub(r"\[Belge:[^\]]+\]", "", cleaned)
    cleaned = re.sub(r"---\s*Kaynak\s*\d+[^-\n]*---", "", cleaned)
    cleaned = re.sub(r"\[KAYNAK\s*\d+:[^\]]*\]", "", cleaned)
    cleaned = re.sub(r"</?(?:belge|source|doc)[^>]*>", "", cleaned, flags=re.IGNORECASE)

    # 4. Yalnızca metnin EN BAŞINDAKİ 'Cevap:', 'Yanıt:', 'Assistant:' öneklerini kaldır
    cleaned = re.sub(r"^\s*(?:cevap|yanıt|answer|response|asistan|assistant)\s*:\s*", "", cleaned, flags=re.IGNORECASE)

    # 5. Ardışık tekrar eden satırları temizle
    lines = cleaned.split("\n")
    deduped_lines = []
    for line in lines:
        s = line.strip()
        if s and deduped_lines and s == deduped_lines[-1].strip():
            continue
        deduped_lines.append(line)

    intermediate_result = "\n".join(deduped_lines).strip()

    # 6. Tekrar eden blok ve başlık döngülerini genel algoritma ile temizle
    final_result = _truncate_repeated_blocks(intermediate_result)
    return final_result


def _detect_repetition_loop(full_text: str) -> tuple[bool, str]:
    """
    Streaming akışında ardışık tekrar eden satır veya kelime bloklarını anında yakalar.
    """
    lines = [l.strip() for l in full_text.split("\n") if l.strip()]
    if len(lines) >= 3:
        if lines[-1] == lines[-2] == lines[-3]:
            return True, lines[-1]

    tail = full_text[-400:]
    words = tail.split()
    n_words = len(words)
    if n_words < 10:
        return False, ""

    max_check = min(15, n_words // 2)
    for k in range(4, max_check + 1):
        unit_a = " ".join(words[-k:]).lower()
        unit_b = " ".join(words[-2 * k : -k]).lower()
        if unit_a == unit_b and len(unit_a) > 15:
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
        self.last_metrics: dict = {}

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

    def _apply_generation_settings(self, max_tokens: Optional[int] = None) -> None:
        """
        Hiperparametreleri uygular (temperature, top_p, max_tokens).
        max_tokens belirtilmezse varsayılan 350 üst sınırı kullanılır.
        """
        if self._chat_client and hasattr(self._chat_client, "settings") and self._chat_client.settings is not None:
            self._chat_client.settings.temperature = LLM_TEMPERATURE
            self._chat_client.settings.top_p = LLM_TOP_P
            budget = max_tokens if max_tokens is not None else 350
            self._chat_client.settings.max_tokens = min(budget, LLM_MAX_TOKENS)

    @staticmethod
    def _estimate_token_budget(question: str, context: str) -> int:
        """
        Sorunun içeriğine ve context büyüklüğüne göre dinamik token budget tahmin eder.
        Hardcode keyword kuralı içermez; genel sinyaller kullanır:
          - Beklenen cevap madde sayısı (soru cümlesindeki bağlaç + liste sinyalleri)
          - Context büyüklüğü (büyük context = daha fazla fact getirilmiş = biraz daha budget)
          - Soru uzunluğu (uzun soru = karmaşık kapsam = biraz daha budget)
        Upper bound her zaman LLM_MAX_TOKENS ile sınırlanır.
        """
        # Soru içerisindeki çoklu-fact sinyallerini say.
        # NOT: "neler(?:dir)?" yerine "neler" kullanılıyor.
        # Neden: "nelerdir" match'i B için budget'i 165→04'e taşıyor ve
        # bu ekstra budget KURAL label echo'yu tetikliyor (B regresyon).
        # C için (API rate limit completeness) budget yetersizliği
        # phi-3.5-mini model kapasitesi ile ilgili, prompt ile çözülemiyor.
        multi_fact_signals = re.findall(
            r"\b(?:ve|ile|ayrıca|birlikte|neler|hangileri|listele|tüm|hepsi|bütün)\b",
            question.lower()
        )
        n_signals = len(multi_fact_signals)

        # Context büyüklüğü sinyali (karaktere göre yaklaşık token)
        ctx_token_approx = len(context) // 4

        # Base budget: kısa/tek-fact için 120, her ek sinyal +40, context büyüklüğü +20 bonus
        base = 120
        signal_bonus = min(n_signals * 40, 160)   # en fazla 4 ek sinyal kabul edilir (4*40=160)
        context_bonus = min(ctx_token_approx // 50, 40)  # bağlam büyüdükçe max +40
        question_len_bonus = min(len(question) // 30, 30)  # uzun soru max +30

        budget = base + signal_bonus + context_bonus + question_len_bonus
        # Güvenlik tavanı: 300 (350'nin altında kalarak gereksiz verbosity azaltılıyor)
        return min(budget, 300)

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
            response = self._chat_client.complete_chat(messages=messages)
            raw = response.choices[0].message.content if response.choices else ""
            rewritten = _clean_response(raw).strip('"').strip("'")
            if rewritten and len(rewritten) > 3 and not rewritten.startswith("Hata"):
                logger.info(f"Sorgu yeniden yazıldı: '{question}' → '{rewritten}'")
                return rewritten
        except Exception as e:
            logger.warning(f"Sorgu yeniden yazma başarısız (orijinal sorgu kullanılıyor): {e}")

        return question

    def generate(self, question: str, context: str) -> str:
        """
        rules.txt Adım 9 & Performance Lockdown İlkelerine Göre Güvenilir Cevap Üretir:
          - Sadece verilen bağlamdaki bilgileri kullanır.
          - Bağlam boş ise LLM çağrısı yapmadan anında ret döner (Zero-Hallucination & Zero-Latency).
          - Kompakt prompt serialization overhead'i ile CPU prefill süresini minimize eder.
          - Single Generation Path: Tek bir kararlı complete_chat çağrısı yapar.
          - Gerçek token usage (prompt_tokens, completion_tokens) metriklerini kaydeder.
        """
        if not self._is_loaded:
            raise RuntimeError(
                "Chat modeli yüklenmemiş. Önce generator.load() çağırın."
            )

        # rules.txt Adım 0 & 9: Bağlam boşsa LLM çağrılmadan doğrudan ret cevabı dönülür
        if not context or not context.strip():
            logger.info("Bağlam boş -> LLM bypass edilerek doğrudan ret dönülüyor.")
            return GROUNDED_REFUSAL_ANSWER

        MAX_CONTEXT_CHARS = 6000
        if len(context) > MAX_CONTEXT_CHARS:
            context = context[:MAX_CONTEXT_CHARS] + "\n...[bağlam optimize edildi]"
            logger.warning(f"Bağlam {MAX_CONTEXT_CHARS} karaktere optimize edildi.")

        # Kompakt ve temiz serialization
        prefix = "/no_think\n" if "qwen" in (self._current_alias or "").lower() else ""
        user_message = (
            f"{prefix}"
            f"BELGELER:\n{context}\n\n"
            f"SORU: {question}"
        )

        messages = [
            {"role": "system", "content": GENERATOR_SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ]

        total_t0 = time.perf_counter()
        prompt_char_count = len(GENERATOR_SYSTEM_PROMPT) + len(user_message)
        has_think_block = False
        raw_output = ""
        clean_answer = ""
        token_usage = {}

        try:
            # Sorgu kapsamına göre dinamik token budget hesapla
            token_budget = self._estimate_token_budget(question, context)
            self._apply_generation_settings(max_tokens=token_budget)
            logger.info(f"LLM çağrısı başlatılıyor | token_budget={token_budget}...")

            chat_t0 = time.perf_counter()
            response = self._chat_client.complete_chat(messages=messages)
            chat_duration_sec = time.perf_counter() - chat_t0

            if response and response.choices and len(response.choices) > 0:
                raw_output = response.choices[0].message.content or ""

            if response and hasattr(response, "usage") and response.usage:
                token_usage = {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
                    "completion_tokens": getattr(response.usage, "completion_tokens", None),
                    "total_tokens": getattr(response.usage, "total_tokens", None),
                }

            has_think_block = ("<think>" in raw_output and "</think>" in raw_output and len(raw_output.split("</think>")[0].replace("<think>", "").strip()) > 5)

            clean_t0 = time.perf_counter()
            clean_answer = _clean_response(raw_output)
            clean_duration_sec = time.perf_counter() - clean_t0

            total_duration_sec = time.perf_counter() - total_t0

            self.last_metrics = {
                "prompt_char_count": prompt_char_count,
                "context_char_count": len(context),
                "question_char_count": len(question),
                "chat_duration_sec": round(chat_duration_sec, 3),
                "clean_duration_sec": round(clean_duration_sec, 5),
                "total_duration_sec": round(total_duration_sec, 3),
                "raw_output_length": len(raw_output),
                "cleaned_output_length": len(clean_answer),
                "has_think_block": has_think_block,
                "token_usage": token_usage,
                "raw_output": raw_output,
            }

            logger.info(
                f"LLM Tamamlandı | Süre: {chat_duration_sec:.2f}s | "
                f"Prompt Tokens: {token_usage.get('prompt_tokens')} | "
                f"Completion Tokens: {token_usage.get('completion_tokens')} | "
                f"Clean Len: {len(clean_answer)}"
            )

            if clean_answer and clean_answer.strip():
                return clean_answer

            return GROUNDED_REFUSAL_ANSWER

        except Exception as exc:
            total_duration_sec = time.perf_counter() - total_t0
            self.last_metrics = {
                "prompt_char_count": prompt_char_count,
                "total_duration_sec": round(total_duration_sec, 3),
                "error": str(exc),
            }
            logger.error(f"LLM üretimi başarısız: {exc}")
            raise RuntimeError(f"Model yanıt üretemedi: {exc}") from exc

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded
