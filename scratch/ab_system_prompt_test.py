"""
scratch/ab_system_prompt_test.py

System prompt optimizasyon A/B testi.
- Baseline: mevcut GENERATOR_SYSTEM_PROMPT (~384 token)
- Candidate: sıkıştırılmış semantik eşdeğer
- Aynı model, hardware, context, generation settings
"""
import sys
import time

sys.path.insert(0, r"c:\Projects\local-rag-project")

from rag.pipeline import RAGPipeline
from rag.generator import GENERATOR_SYSTEM_PROMPT as BASELINE_PROMPT, GROUNDED_REFUSAL_ANSWER

# ─────────────────────────────────────────────
# ADAY PROMPT versiyonları — sırasıyla denenir
# ─────────────────────────────────────────────

# v1: Agresif sıkıştırma (~%35 azaltım hedefi)
CANDIDATE_v1 = (
    "Kurumsal Türkçe RAG asistanısın. "
    "KAPSAM: Yalnızca soruyla doğrudan ilgili belge bilgilerini kullan; "
    "belgede bulunan fakat sorunun kapsamı dışındaki bilgileri, sayıları veya kuralları cevaba ekleme. "
    "BÜTÜNLÜK: Soru birden fazla konu/kural içeriyorsa tümünü ayrı madde halinde ver; hiçbir istenen maddeyi atlama. "
    "SAYISAL DOĞRULUK: Sayısal değerleri (saniye, dakika, gün, limit, adet) kaynaktan birebir aktar; birim dönüştürme. "
    "RED: Belgede yoksa yalnızca 'Verilen belgelerde bu bilgi yer almamaktadır.' yaz. "
    "FORMAT: Kısa maddeler; giriş/özet/tekrar yok."
)

# v2: Orta sıkıştırma — biraz daha açıklayıcı KAPSAM koruma
CANDIDATE_v2 = (
    "Kurumsal Türkçe soru-cevap asistanısın. "
    "KAPSAM: Sorunun tam olarak ne sorduğunu belirle. "
    "Yalnızca soruyu doğrudan yanıtlayan belge bilgilerini kullan; "
    "belgede aynı anda bulunan fakat soru kapsamı dışındaki bilgileri, süreleri veya limitleri cevaba dahil etme. "
    "BÜTÜNLÜK: Soru açıkça birden fazla konu istiyorsa her birini ayrı madde halinde yaz; hiçbir maddeyi atlama. "
    "SAYISAL DOĞRULUK: Sayısal değerleri (saniye, dakika, gün, adet, limit) kaynaktan birebir aktar; "
    "eşdeğer birime çevirme veya kaynak ifadeyi değiştirme. "
    "RED: Kaynakta bulunmayan bilgiler için yalnızca 'Verilen belgelerde bu bilgi yer almamaktadır.' yaz. "
    "FORMAT: Kısa, düz maddeler; giriş cümlesi, özet veya tekrar yok."
)

# ─────────────────────────────────────────────
BENCHMARK_QUERIES = [
    {
        "id": "Q1_PASSWORD",
        "question": "Kullanıcı girişinde şifre kuralları ve hatalı denemede hesap bloke süreleri nelerdir?",
        "must_contain": ["8", "15"],
        "must_not_contain": ["30 gün", "180 saniye", "OTP"],
        "label": "Çok parçalı, scope isolation kritik"
    },
    {
        "id": "Q2_API_LIMITS",
        "question": "API istek sınırları ve rate limiting kuralları nelerdir?",
        "must_contain": ["60", "300"],
        "must_not_contain": [],
        "label": "Numeric multi-fact"
    },
    {
        "id": "Q3_BRAND_COLOR",
        "question": "Mobil tasarım kılavuzuna göre birincil marka rengi ve ikincil vurgu rengi nedir?",
        "must_contain": ["#0E2538", "#2563EB"],
        "must_not_contain": [],
        "label": "Color extraction"
    },
    {
        "id": "Q4_POSTGRES_REFUSAL",
        "question": "PostgreSQL veritabanı replikasyon ve failover ayarları nasıl yapılır?",
        "must_contain": ["Verilen belgelerde bu bilgi yer almamaktadır."],
        "must_not_contain": [],
        "label": "Negative refusal"
    },
]

MULTIDOC_QUERY = {
    "id": "Q_MULTIDOC",
    "question": "API istek sınırları ve mobil uygulama birincil marka rengi nedir?",
    "must_contain": ["#0E2538", "60", "300"],
    "must_not_contain": [],
    "label": "Multi-doc completeness"
}
ALL_QUERIES = BENCHMARK_QUERIES + [MULTIDOC_QUERY]


def measure_prompt_tokens(client, prompt_text: str) -> int:
    """Tek bir prompt metninin token sayısını ölç (system + dummy user)."""
    msgs = [
        {"role": "system", "content": prompt_text},
        {"role": "user", "content": "test"}
    ]
    resp = client.complete_chat(messages=msgs)
    sys_plus_dummy = resp.usage.prompt_tokens if resp and resp.usage else 0
    dummy = [{"role": "user", "content": "test"}]
    resp2 = client.complete_chat(messages=dummy)
    dummy_tok = resp2.usage.prompt_tokens if resp2 and resp2.usage else 0
    return sys_plus_dummy - dummy_tok


def run_benchmark_with_prompt(pipeline: RAGPipeline, system_prompt: str, label: str) -> list[dict]:
    """Belirli bir system prompt ile tüm benchmark sorgularını çalıştır."""
    import rag.generator as gen_module
    original_prompt = gen_module.GENERATOR_SYSTEM_PROMPT
    gen_module.GENERATOR_SYSTEM_PROMPT = system_prompt
    
    results = []
    print(f"\n{'─'*70}")
    print(f"PROMPT: {label}")
    print(f"{'─'*70}")
    
    try:
        for q_data in ALL_QUERIES:
            qid = q_data["id"]
            question = q_data["question"]
            
            t_start = time.perf_counter()
            chunks = pipeline._retriever.get_top_chunks(question, top_k=2)
            context = pipeline._retriever.format_context(chunks)
            
            if not chunks:
                answer = GROUNDED_REFUSAL_ANSWER
                t_total = time.perf_counter() - t_start
                ttft = 0.0
                out_tok = 0
                prompt_tok = 0
            else:
                answer = pipeline._generator.generate(question, context)
                metrics = pipeline._generator.last_metrics
                tok = metrics.get("token_usage", {})
                prompt_tok = tok.get("prompt_tokens", 0)
                out_tok = tok.get("completion_tokens", 0)
                ttft = metrics.get("ttft_sec", 0.0)
                t_total = time.perf_counter() - t_start
            
            # Accuracy check
            must_contain = q_data["must_contain"]
            must_not = q_data["must_not_contain"]
            ans_lower = answer.lower()
            
            missing = [kw for kw in must_contain if kw.lower() not in ans_lower]
            leaked = [kw for kw in must_not if kw.lower() in ans_lower]
            
            passed = (len(missing) == 0 and len(leaked) == 0)
            status = "PASS" if passed else "FAIL"
            
            result = {
                "qid": qid,
                "status": status,
                "missing": missing,
                "leaked": leaked,
                "prompt_tok": prompt_tok,
                "out_tok": out_tok,
                "ttft": ttft,
                "total": t_total,
                "answer": answer[:250]
            }
            results.append(result)
            
            print(f"  [{status}] {qid:<22} | PromptTok={prompt_tok:<5} | TTFT={ttft:.2f}s | Total={t_total:.2f}s | OutTok={out_tok}")
            if missing:
                print(f"         ⚠ MISSING: {missing}")
            if leaked:
                print(f"         ✗ LEAKED:  {leaked}")
            print(f"         → {answer[:150].strip()}")
    finally:
        gen_module.GENERATOR_SYSTEM_PROMPT = original_prompt
    
    return results



def summarize(results: list[dict], label: str, sys_tok: int):
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    pos_results = [r for r in results if r["prompt_tok"] > 0]
    avg_ptok = sum(r["prompt_tok"] for r in pos_results) / len(pos_results) if pos_results else 0
    avg_ttft = sum(r["ttft"] for r in pos_results) / len(pos_results) if pos_results else 0
    avg_total = sum(r["total"] for r in results) / len(results)
    return {
        "label": label,
        "sys_tok": sys_tok,
        "avg_prompt_tok": avg_ptok,
        "avg_ttft": avg_ttft,
        "avg_total": avg_total,
        "pass_count": pass_count,
        "total_count": len(results),
    }


def main():
    print("=" * 70)
    print("SYSTEM PROMPT A/B OPTIMIZASYON TESTİ")
    print("=" * 70)
    
    p = RAGPipeline()
    p.load()
    client = p._generator._chat_client
    
    # Generator'da _system_prompt attribute'u yoksa ekleyelim
    gen = p._generator
    
    # Token sayılarını ölç
    print("\n[TOKEN ÖLÇÜMÜ]")
    baseline_sys_tok = measure_prompt_tokens(client, BASELINE_PROMPT)
    v1_sys_tok = measure_prompt_tokens(client, CANDIDATE_v1)
    v2_sys_tok = measure_prompt_tokens(client, CANDIDATE_v2)
    
    print(f"  BASELINE token: {baseline_sys_tok}")
    print(f"  CANDIDATE_v1 token: {v1_sys_tok}  ({100*(1-v1_sys_tok/baseline_sys_tok):.1f}% azaltım)")
    print(f"  CANDIDATE_v2 token: {v2_sys_tok}  ({100*(1-v2_sys_tok/baseline_sys_tok):.1f}% azaltım)")
    
    # Check generator's internal system prompt method
    # We need to patch into the generate() call
    # Find where system prompt is injected
    import inspect
    gen_source = inspect.getsource(gen.generate)
    if "_system_prompt" in gen_source:
        print("\n[INFO] Generator uses self._system_prompt attribute.")
    elif "GENERATOR_SYSTEM_PROMPT" in gen_source:
        print("\n[INFO] Generator uses module-level GENERATOR_SYSTEM_PROMPT.")
    else:
        print("\n[INFO] System prompt injection location: unknown — check generate() method.")
    
    # Run BASELINE
    baseline_results = run_benchmark_with_prompt(p, BASELINE_PROMPT, f"BASELINE (~{baseline_sys_tok} tok)")
    
    # Run CANDIDATE_v1
    v1_results = run_benchmark_with_prompt(p, CANDIDATE_v1, f"CANDIDATE_v1 (~{v1_sys_tok} tok, {100*(1-v1_sys_tok/baseline_sys_tok):.1f}% küçük)")
    
    # Run CANDIDATE_v2
    v2_results = run_benchmark_with_prompt(p, CANDIDATE_v2, f"CANDIDATE_v2 (~{v2_sys_tok} tok, {100*(1-v2_sys_tok/baseline_sys_tok):.1f}% küçük)")
    
    # Summary
    b_sum = summarize(baseline_results, "BASELINE", baseline_sys_tok)
    v1_sum = summarize(v1_results, "CANDIDATE_v1", v1_sys_tok)
    v2_sum = summarize(v2_results, "CANDIDATE_v2", v2_sys_tok)
    
    print("\n" + "=" * 70)
    print("KARŞILAŞTIRMA TABLOSU")
    print("=" * 70)
    print(f"{'Versiyon':<20} | {'SysTok':<8} | {'AvgPTok':<9} | {'AvgTTFT':<9} | {'AvgTotal':<10} | {'Pass/Total'}")
    print("-" * 70)
    for s in [b_sum, v1_sum, v2_sum]:
        print(f"{s['label']:<20} | {s['sys_tok']:<8} | {s['avg_prompt_tok']:<9.0f} | {s['avg_ttft']:<9.2f}s | {s['avg_total']:<10.2f}s | {s['pass_count']}/{s['total_count']}")
    
    print("\n" + "=" * 70)
    print("SON KARAR")
    print("=" * 70)
    for s, results in [(v1_sum, v1_results), (v2_sum, v2_results)]:
        all_pass = s["pass_count"] == s["total_count"]
        latency_gain = b_sum["avg_ttft"] - s["avg_ttft"]
        total_gain = b_sum["avg_total"] - s["avg_total"]
        tok_reduction = (1 - s["sys_tok"] / b_sum["sys_tok"]) * 100
        
        if all_pass and latency_gain > 0.5:
            verdict = "ACCEPT"
            reason = f"Doğruluk korunmuş, TTFT -{latency_gain:.1f}s, Total -{total_gain:.1f}s kazanımı var."
        elif all_pass:
            verdict = "NO-GAIN"
            reason = f"Doğruluk korunmuş ama anlamlı latency kazanımı yok (ΔTTFT={latency_gain:.2f}s)."
        else:
            verdict = "REJECT"
            fails = [r for r in results if r["status"] == "FAIL"]
            reason = f"Accuracy/logic regresyonu: {[f['qid'] for f in fails]}"
        
        print(f"\n{s['label']:}")
        print(f"  Token azaltım:  {tok_reduction:.1f}% ({b_sum['sys_tok']} → {s['sys_tok']})")
        print(f"  TTFT değişimi:  {latency_gain:+.2f}s")
        print(f"  Total değişimi: {total_gain:+.2f}s")
        print(f"  Accuracy:       {s['pass_count']}/{s['total_count']}")
        print(f"  KARAR: *** {verdict} ***")
        print(f"  Neden: {reason}")

if __name__ == "__main__":
    main()
