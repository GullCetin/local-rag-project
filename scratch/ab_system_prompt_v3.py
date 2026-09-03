"""
scratch/ab_system_prompt_v3.py

Sadece v3 adayını test eder:
- KURAL 1 (KAPSAM) tamamen dokunulmaz (scope isolation için kritik)
- KURAL 2, 3, 4 minimal kelime tasarrufu
- KURAL 5 (FORMAT) agresif sıkıştırma (en az kritik)
"""
import sys
import time

sys.path.insert(0, r"c:\Projects\local-rag-project")

from rag.pipeline import RAGPipeline
from rag.generator import GENERATOR_SYSTEM_PROMPT as BASELINE_PROMPT, GROUNDED_REFUSAL_ANSWER

# ─────────────────────────────────────────────
# Baseline
# ─────────────────────────────────────────────
# "Sen kurumsal bir Türkçe soru-cevap asistanısın. "
# "KURAL 1 (KAPSAM): Soruyu dikkatle oku ve tam olarak ne sorulduğunu belirle. "
# "Yalnızca soruyu doğrudan yanıtlayan bilgileri kullan; "
# "belgede soruyla ilgisiz başka bilgiler, süreler veya limitler olsa bile onları cevaba dahil etme. "
# "KURAL 2 (BÜTÜNLÜK): Soruda açıkça birden fazla konu veya kural isteniyorsa her birini ayrı madde halinde yaz; hiçbir istened maddeyi atlama. "
# "KURAL 3 (SAYISAL DOĞRULUK): Belgedeki sayısal değerleri (saniye, dakika, gün, rakam, limit) birebir aktar; eşdeğer birime çevirme veya kaynak ifadeyi değiştirme. "
# "KURAL 4 (RED): Kaynakta bulunmayan bilgiler için yalnızca 'Verilen belgelerde bu bilgi yer almamaktadır.' yaz. "
# "KURAL 5 (FORMAT): Düz maddeler halinde, kısa ve doğrudan yaz; giriş cümlesi, genel açıklama, özet veya tekrar yazma."

# ─────────────────────────────────────────────
# v3: Sadece güvenli, semantiği bozmayan kısımlarda tasarruf
# Değişiklikler:
#   [role]   "Sen kurumsal bir Türkçe soru-cevap asistanısın." → "Kurumsal Türkçe soru-cevap asistanısın." (-2 tok)
#   [K1]     DOKUNULMADI — verbatim korundu
#   [K2]     "isteniyorsa her birini ayrı madde halinde yaz; hiçbir istened maddeyi atlama"
#            → "isteniyorsa her birini ayrı maddede yaz; atlama" (-5 tok, typo "istened" düzeltildi)
#   [K3]     "(saniye, dakika, gün, rakam, limit)" → "(saniye, dakika, gün, limit)" (-1 tok, "rakam" diğerleri içinde implicit)
#            "eşdeğer birime çevirme veya" → "birime çevirme veya" (-2 tok)
#   [K4]     "Kaynakta bulunmayan bilgiler için yalnızca" → "Kaynakta bulunmayan bilgi için yalnızca" (-1 tok)
#   [K5]     "Düz maddeler halinde, kısa ve doğrudan yaz; giriş cümlesi, genel açıklama, özet veya tekrar yazma."
#            → "Kısa, düz maddeler; giriş, özet veya tekrar yok." (-12 tok)
#   Toplam tahmini tasarruf: ~23 token (%6)
# ─────────────────────────────────────────────
CANDIDATE_v3 = (
    "Kurumsal Türkçe soru-cevap asistanısın. "
    "KURAL 1 (KAPSAM): Soruyu dikkatle oku ve tam olarak ne sorulduğunu belirle. "
    "Yalnızca soruyu doğrudan yanıtlayan bilgileri kullan; "
    "belgede soruyla ilgisiz başka bilgiler, süreler veya limitler olsa bile onları cevaba dahil etme. "
    "KURAL 2 (BÜTÜNLÜK): Soruda açıkça birden fazla konu veya kural isteniyorsa her birini ayrı maddede yaz; atlama. "
    "KURAL 3 (SAYISAL DOĞRULUK): Belgedeki sayısal değerleri (saniye, dakika, gün, limit) birebir aktar; birime çevirme veya kaynak ifadeyi değiştirme. "
    "KURAL 4 (RED): Kaynakta bulunmayan bilgi için yalnızca 'Verilen belgelerde bu bilgi yer almamaktadır.' yaz. "
    "KURAL 5 (FORMAT): Kısa, düz maddeler; giriş, özet veya tekrar yok."
)

ALL_QUERIES = [
    {
        "id": "Q1_PASSWORD",
        "question": "Kullanıcı girişinde şifre kuralları ve hatalı denemede hesap bloke süreleri nelerdir?",
        "must_contain": ["8", "15"],
        "must_not_contain": ["30 gün", "180 saniye", "OTP"],
    },
    {
        "id": "Q2_API_LIMITS",
        "question": "API istek sınırları ve rate limiting kuralları nelerdir?",
        "must_contain": ["60", "300"],
        "must_not_contain": [],
    },
    {
        "id": "Q3_BRAND_COLOR",
        "question": "Mobil tasarım kılavuzuna göre birincil marka rengi ve ikincil vurgu rengi nedir?",
        "must_contain": ["#0E2538", "#2563EB"],
        "must_not_contain": [],
    },
    {
        "id": "Q4_POSTGRES_REFUSAL",
        "question": "PostgreSQL veritabanı replikasyon ve failover ayarları nasıl yapılır?",
        "must_contain": ["Verilen belgelerde bu bilgi yer almamaktadır."],
        "must_not_contain": [],
    },
    {
        "id": "Q_MULTIDOC",
        "question": "API istek sınırları ve mobil uygulama birincil marka rengi nedir?",
        "must_contain": ["#0E2538", "60", "300"],
        "must_not_contain": [],
    },
]


def measure_sys_tokens(client, prompt_text: str) -> int:
    msgs_with = [{"role": "system", "content": prompt_text}, {"role": "user", "content": "test"}]
    msgs_without = [{"role": "user", "content": "test"}]
    r1 = client.complete_chat(messages=msgs_with)
    r2 = client.complete_chat(messages=msgs_without)
    tok1 = r1.usage.prompt_tokens if r1 and r1.usage else 0
    tok2 = r2.usage.prompt_tokens if r2 and r2.usage else 0
    return tok1 - tok2


def run_with_prompt(pipeline, system_prompt: str, label: str) -> list[dict]:
    import rag.generator as gen_module
    original = gen_module.GENERATOR_SYSTEM_PROMPT
    gen_module.GENERATOR_SYSTEM_PROMPT = system_prompt
    results = []
    print(f"\n--- {label} ---")
    try:
        for q in ALL_QUERIES:
            t0 = time.perf_counter()
            chunks = pipeline._retriever.get_top_chunks(q["question"], top_k=2)
            context = pipeline._retriever.format_context(chunks)
            if not chunks:
                answer = GROUNDED_REFUSAL_ANSWER
                prompt_tok, out_tok, ttft = 0, 0, 0.0
            else:
                answer = pipeline._generator.generate(q["question"], context)
                m = pipeline._generator.last_metrics
                tok = m.get("token_usage", {})
                prompt_tok = tok.get("prompt_tokens", 0)
                out_tok = tok.get("completion_tokens", 0)
                ttft = m.get("ttft_sec", 0.0)
            t_total = time.perf_counter() - t0

            ans_l = answer.lower()
            missing = [kw for kw in q["must_contain"] if kw.lower() not in ans_l]
            leaked = [kw for kw in q["must_not_contain"] if kw.lower() in ans_l]
            status = "PASS" if not missing and not leaked else "FAIL"

            results.append({
                "qid": q["id"], "status": status, "missing": missing, "leaked": leaked,
                "prompt_tok": prompt_tok, "out_tok": out_tok, "ttft": ttft, "total": t_total,
                "answer": answer[:250]
            })
            print(f"  [{status}] {q['id']:<22} | PTok={prompt_tok:<5} | TTFT={ttft:.2f}s | Total={t_total:.2f}s | OutTok={out_tok}")
            if missing: print(f"         MISSING: {missing}")
            if leaked:  print(f"         LEAKED:  {leaked}")
            print(f"         -> {answer[:160].strip()}")
    finally:
        gen_module.GENERATOR_SYSTEM_PROMPT = original
    return results


def main():
    print("=" * 70)
    print("SYSTEM PROMPT v3 CONTROLLED A/B TEST")
    print("=" * 70)

    p = RAGPipeline()
    p.load()
    client = p._generator._chat_client

    base_tok = measure_sys_tokens(client, BASELINE_PROMPT)
    v3_tok = measure_sys_tokens(client, CANDIDATE_v3)
    reduction = (1 - v3_tok / base_tok) * 100
    print(f"\n[TOKEN] BASELINE: {base_tok} tok | v3: {v3_tok} tok | Azaltim: {reduction:.1f}%")
    print(f"\n[BASELINE PROMPT]:\n{BASELINE_PROMPT}\n")
    print(f"[v3 PROMPT]:\n{CANDIDATE_v3}\n")

    baseline_results = run_with_prompt(p, BASELINE_PROMPT, f"BASELINE ({base_tok} tok)")
    v3_results = run_with_prompt(p, CANDIDATE_v3, f"CANDIDATE_v3 ({v3_tok} tok, -{reduction:.1f}%)")

    # Summary
    def avg(lst, key):
        vals = [r[key] for r in lst if r[key] > 0]
        return sum(vals) / len(vals) if vals else 0.0

    b_pass = sum(1 for r in baseline_results if r["status"] == "PASS")
    v3_pass = sum(1 for r in v3_results if r["status"] == "PASS")

    print("\n" + "=" * 70)
    print("KARSILASTIRMA")
    print("=" * 70)
    print(f"{'':20} | {'SysTok':<8} | {'AvgPTok':<9} | {'AvgTTFT':<9} | {'AvgTotal':<10} | {'Pass/Total'}")
    print("-" * 70)

    for label, results, sys_tok in [
        ("BASELINE", baseline_results, base_tok),
        ("CANDIDATE_v3", v3_results, v3_tok),
    ]:
        ap = avg(results, "prompt_tok")
        at = avg(results, "ttft")
        atotal = sum(r["total"] for r in results) / len(results)
        pc = sum(1 for r in results if r["status"] == "PASS")
        print(f"{label:<20} | {sys_tok:<8} | {ap:<9.0f} | {at:<9.2f}s | {atotal:<10.2f}s | {pc}/{len(results)}")

    print("\n[SON KARAR]")
    ttft_gain = avg(baseline_results, "ttft") - avg(v3_results, "ttft")
    total_gain = (sum(r["total"] for r in baseline_results) / len(baseline_results)) - \
                 (sum(r["total"] for r in v3_results) / len(v3_results))

    all_v3_pass = v3_pass >= b_pass  # v3 en az baseline kadar geçmeli
    # Q1 scope isolation hiçbir zaman gerilemeyemez
    q1_v3 = next((r for r in v3_results if r["qid"] == "Q1_PASSWORD"), None)
    q1_ok = q1_v3 and q1_v3["status"] == "PASS"

    if q1_ok and all_v3_pass and ttft_gain > 0.3:
        verdict = "ACCEPT"
    elif q1_ok and all_v3_pass:
        verdict = "NO-GAIN"
    else:
        verdict = "REJECT"
        fails = [r["qid"] for r in v3_results if r["status"] == "FAIL"]
        print(f"  Regresyon: {fails}")

    print(f"  v3 Token azaltim: {reduction:.1f}% ({base_tok} -> {v3_tok})")
    print(f"  TTFT degisimi:    {ttft_gain:+.2f}s")
    print(f"  Total degisimi:   {total_gain:+.2f}s")
    print(f"  Q1 scope:         {'PASS' if q1_ok else 'FAIL'}")
    print(f"  Accuracy:         {v3_pass}/{len(v3_results)}")
    print(f"  *** {verdict} ***")


if __name__ == "__main__":
    main()
