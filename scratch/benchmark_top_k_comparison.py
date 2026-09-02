"""
scratch/benchmark_top_k_comparison.py
Top-k=2 vs Top-k=1 latency ve accuracy karşılaştırma testi.
"""
import sys
import time

sys.path.insert(0, r"c:\Projects\local-rag-project")

from rag.pipeline import RAGPipeline

TEST_CASES = [
    {
        "id": "Q1_PASSWORD",
        "question": "Kullanıcı girişinde şifre kuralları ve hatalı denemede hesap bloke süreleri nelerdir?",
        "expected": ["8", "15"],
        "forbidden": ["30 gün", "180 saniye", "OTP"],
    },
    {
        "id": "Q2_API_LIMITS",
        "question": "API istek sınırları ve rate limiting kuralları nelerdir?",
        "expected": ["60", "300"],
        "forbidden": [],
    },
    {
        "id": "Q3_BRAND_COLOR",
        "question": "Mobil tasarım kılavuzuna göre birincil marka rengi ve ikincil vurgu rengi nedir?",
        "expected": ["#0E2538", "#2563EB"],
        "forbidden": [],
    },
    {
        "id": "Q_MULTIDOC",
        "question": "Mobil tasarım kılavuzundaki renkler ile API güvenlik kuralları nelerdir?",
        "expected": ["#0E2538", "60", "300"], # Hem mobil kılavuz hem API politikasını sorgular
        "forbidden": [],
    },
    {
        "id": "Q4_POSTGRES_REFUSAL",
        "question": "PostgreSQL veritabanı replikasyon ve failover ayarları nasıl yapılır?",
        "expected": ["Verilen belgelerde bu bilgi yer almamaktadır."],
        "forbidden": [],
    }
]

def run_evaluation(pipeline, top_k_val):
    print(f"\n{'='*70}")
    print(f"EVALUATION: TOP_K = {top_k_val}")
    print(f"{'='*70}")
    
    results = []
    for item in TEST_CASES:
        qid = item["id"]
        q = item["question"]
        t0 = time.perf_counter()
        
        chunks = pipeline._retriever.get_top_chunks(q, top_k=top_k_val)
        t_ret = time.perf_counter() - t0
        
        if not chunks:
            ans = "Verilen belgelerde bu bilgi yer almamaktadır."
            ttft = 0.0
            t_gen = 0.0
            prompt_tok = 0
            comp_tok = 0
        else:
            context = pipeline._retriever.format_context(chunks)
            ans = pipeline._generator.generate(q, context)
            metrics = getattr(pipeline._generator, "last_metrics", {})
            ttft = metrics.get("ttft_sec") or 0.0
            t_gen = metrics.get("chat_duration_sec") or 0.0
            tok_usage = metrics.get("token_usage", {})
            prompt_tok = tok_usage.get("prompt_tokens") or 0
            comp_tok = tok_usage.get("completion_tokens") or 0
            
        t_total = time.perf_counter() - t0
        
        has_exp = all(e.lower() in ans.lower() for e in item["expected"])
        has_forb = any(f.lower() in ans.lower() for f in item["forbidden"])
        passed = has_exp and not has_forb
        
        print(f"[{qid}] Pass: {passed} | Chunks: {len(chunks)} | PromptTok: {prompt_tok} | TTFT: {ttft:.2f}s | Gen: {t_gen:.2f}s | Total: {t_total:.2f}s")
        print(f"  Preview: {ans[:120]}...")
        
        results.append({
            "id": qid,
            "top_k": top_k_val,
            "pass": passed,
            "prompt_tokens": prompt_tok,
            "ttft": ttft,
            "t_gen": t_gen,
            "t_total": t_total,
            "completion_tokens": comp_tok,
            "chunks_used": len(chunks),
        })
    return results

def main():
    p = RAGPipeline()
    p.load()
    
    res_k2 = run_evaluation(p, top_k_val=2)
    res_k1 = run_evaluation(p, top_k_val=1)
    
    print("\n" + "="*70)
    print("COMPARISON SUMMARY (top_k=2 vs top_k=1)")
    print("="*70)
    print(f"{'QID':<20} | {'Metric':<12} | {'Top-K=2':<12} | {'Top-K=1':<12} | {'Fark / Kazanç'}")
    print("-"*70)
    for r2, r1 in zip(res_k2, res_k1):
        qid = r2["id"]
        print(f"{qid:<20} | {'Total Sec':<12} | {r2['t_total']:<12.2f} | {r1['t_total']:<12.2f} | {r2['t_total'] - r1['t_total']:+.2f}s")
        print(f"{'':<20} | {'TTFT':<12} | {r2['ttft']:<12.2f} | {r1['ttft']:<12.2f} | {r2['ttft'] - r1['ttft']:+.2f}s")
        print(f"{'':<20} | {'Prompt Tok':<12} | {r2['prompt_tokens']:<12} | {r1['prompt_tokens']:<12} | {r2['prompt_tokens'] - r1['prompt_tokens']:+d}")
        print(f"{'':<20} | {'Accuracy':<12} | {('PASS' if r2['pass'] else 'FAIL'):<12} | {('PASS' if r1['pass'] else 'FAIL'):<12} | {'KORUNDU' if r1['pass'] else 'BOZULDU'}")
        print("-"*70)

if __name__ == "__main__":
    main()
