"""
scratch/measure_baseline_latency.py
Mevcut pipeline üzerinde 4 referans sorgunun detaylı latency ve doğruluk profilini çıkarır.
"""
import sys
import os
import time
import json

# Add project root to sys.path
sys.path.insert(0, r"c:\Projects\local-rag-project")

from rag.pipeline import RAGPipeline
from config import LLM_MODEL_ALIAS

QUESTIONS = [
    {
        "id": "Q1_PASSWORD",
        "question": "Kullanıcı girişinde şifre kuralları ve hatalı denemede hesap bloke süreleri nelerdir?",
        "expected_facts": ["8", "15"],
        "forbidden_contaminants": ["30 gün", "180 saniye", "OTP"],
        "type": "multi_fact"
    },
    {
        "id": "Q2_API_LIMITS",
        "question": "API istek sınırları ve rate limiting kuralları nelerdir?",
        "expected_facts": ["60", "300"],
        "forbidden_contaminants": [],
        "type": "multi_fact"
    },
    {
        "id": "Q3_BRAND_COLOR",
        "question": "Mobil tasarım kılavuzuna göre birincil marka rengi ve ikincil vurgu rengi nedir?",
        "expected_facts": ["#0E2538", "#2563EB"], # mobil_uygulama_tasarim_kilavuzu.md'deki gerçek değerler
        "forbidden_contaminants": [],
        "type": "short_factual"
    },
    {
        "id": "Q4_POSTGRES_REFUSAL",
        "question": "PostgreSQL veritabanı replikasyon ve failover ayarları nasıl yapılır?",
        "expected_facts": ["Verilen belgelerde bu bilgi yer almamaktadır."],
        "forbidden_contaminants": [],
        "type": "negative_refusal"
    }
]

def main():
    print(f"=== BASELINE LATENCY & ACCURACY BENCHMARK ===")
    print(f"Active Model: {LLM_MODEL_ALIAS}")
    
    pipeline = RAGPipeline()
    print("Loading pipeline...")
    t_load0 = time.perf_counter()
    pipeline.load()
    t_load = time.perf_counter() - t_load0
    print(f"Pipeline loaded in {t_load:.2f}s\n")
    
    results = []
    
    for item in QUESTIONS:
        qid = item["id"]
        q = item["question"]
        print(f"--- [{qid}] {q} ---")
        
        t0 = time.perf_counter()
        
        # 1. Retrieval profile
        t_ret0 = time.perf_counter()
        chunks = pipeline._retriever.get_top_chunks(q)
        t_ret = time.perf_counter() - t_ret0
        
        context = pipeline._retriever.format_context(chunks)
        
        # 2. Generator profile
        t_gen0 = time.perf_counter()
        if not chunks:
            answer = "Verilen belgelerde bu bilgi yer almamaktadır."
            t_gen = time.perf_counter() - t_gen0
            metrics = {}
        else:
            answer = pipeline._generator.generate(q, context)
            t_gen = time.perf_counter() - t_gen0
            metrics = getattr(pipeline._generator, "last_metrics", {})
        
        total_time = time.perf_counter() - t0
        
        token_usage = metrics.get("token_usage", {})
        prompt_tokens = token_usage.get("prompt_tokens", "N/A")
        completion_tokens = token_usage.get("completion_tokens", "N/A")
        
        print(f"Total Time: {total_time:.2f}s | Ret Time: {t_ret:.3f}s | Gen Time: {t_gen:.2f}s")
        print(f"Chunks: {len(chunks)} | Prompt Tokens: {prompt_tokens} | Completion Tokens: {completion_tokens}")
        print(f"Answer:\n{answer}\n")
        
        # Accuracy checks
        has_expected = all(ef.lower() in answer.lower() for ef in item["expected_facts"])
        has_forbidden = any(fc.lower() in answer.lower() for fc in item["forbidden_contaminants"])
        
        passed = has_expected and not has_forbidden
        print(f"Accuracy Check: {'PASS' if passed else 'FAIL'} (Expected: {has_expected}, Forbidden found: {has_forbidden})")
        print("=" * 60)
        
        results.append({
            "id": qid,
            "question": q,
            "total_sec": total_time,
            "ret_sec": t_ret,
            "gen_sec": t_gen,
            "chunks_count": len(chunks),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "answer": answer,
            "pass": passed,
            "metrics": metrics
        })

    # Summary
    print("\n=== SUMMARY ===")
    gen_times = [r["gen_sec"] for r in results if r["chunks_count"] > 0]
    total_times = [r["total_sec"] for r in results]
    comp_tokens = [r["completion_tokens"] for r in results if isinstance(r["completion_tokens"], int)]
    
    print(f"Average Total Latency: {sum(total_times)/len(total_times):.2f}s")
    if gen_times:
        print(f"Average Generation Latency (non-negative): {sum(gen_times)/len(gen_times):.2f}s")
    if comp_tokens:
        print(f"Average Completion Tokens: {sum(comp_tokens)/len(comp_tokens):.1f}")
    print(f"Accuracy: {sum(1 for r in results if r['pass'])}/{len(results)} passed")

if __name__ == "__main__":
    main()
