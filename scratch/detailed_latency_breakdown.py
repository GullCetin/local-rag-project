"""
scratch/detailed_latency_breakdown.py
Mevcut pipeline üzerinde 7 aşamalı ayrıntılı latency ve prefill breakdown profilini çıkarır.
"""
import sys
import os
import time

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
        "expected_facts": ["#0E2538", "#2563EB"],
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

def profile_query(pipeline, q_item):
    q = q_item["question"]
    qid = q_item["id"]
    
    t_start = time.perf_counter()
    
    # 1. Retrieval
    t_ret0 = time.perf_counter()
    chunks = pipeline._retriever.get_top_chunks(q)
    t_ret = time.perf_counter() - t_ret0
    
    # 2. Context Preparation / Formatting
    t_ctx0 = time.perf_counter()
    context = pipeline._retriever.format_context(chunks)
    t_ctx = time.perf_counter() - t_ctx0
    
    # 3. Generation (with TTFT / Prefill and Generation split)
    if not chunks:
        answer = "Verilen belgelerde bu bilgi yer almamaktadır."
        ttft = 0.0
        t_gen = 0.0
        prompt_tokens = 0
        completion_tokens = 0
        finish_reason = "bypass"
    else:
        answer = pipeline._generator.generate(q, context)
        metrics = getattr(pipeline._generator, "last_metrics", {})
        ttft = metrics.get("ttft_sec") or 0.0
        t_gen = metrics.get("chat_duration_sec") or 0.0
        token_usage = metrics.get("token_usage", {})
        prompt_tokens = token_usage.get("prompt_tokens") or 0
        completion_tokens = token_usage.get("completion_tokens") or 0
        finish_reason = metrics.get("finish_reason", "unknown")
        
    t_total = time.perf_counter() - t_start
    
    # Generation execution time after first token
    decode_latency = max(0.0, t_gen - ttft) if ttft > 0 else t_gen
    
    # Accuracy check
    has_expected = all(ef.lower() in answer.lower() for ef in q_item["expected_facts"])
    has_forbidden = any(fc.lower() in answer.lower() for fc in q_item["forbidden_contaminants"])
    passed = has_expected and not has_forbidden
    
    return {
        "id": qid,
        "question": q,
        "chunks_count": len(chunks),
        "chunk_scores": [round(c["score"], 4) for c in chunks],
        "retrieval_sec": round(t_ret, 3),
        "context_prep_sec": round(t_ctx, 5),
        "prompt_tokens": prompt_tokens,
        "ttft_prefill_sec": round(ttft, 3),
        "decode_gen_sec": round(decode_latency, 3),
        "chat_duration_sec": round(t_gen, 3),
        "total_latency_sec": round(t_total, 3),
        "completion_tokens": completion_tokens,
        "finish_reason": finish_reason,
        "answer": answer,
        "pass": passed,
    }

def main():
    print(f"================================================================================")
    print(f"DETAILED LATENCY & PREFILL BREAKDOWN BENCHMARK (Model: {LLM_MODEL_ALIAS})")
    print(f"================================================================================")
    
    pipeline = RAGPipeline()
    pipeline.load()
    
    results = []
    for item in QUESTIONS:
        res = profile_query(pipeline, item)
        results.append(res)
        
        print(f"\n--- [{res['id']}] {res['question']} ---")
        print(f"  * Chunks: {res['chunks_count']} (Scores: {res['chunk_scores']})")
        print(f"  * 1. Retrieval Latency:        {res['retrieval_sec']}s")
        print(f"  * 2. Context Prep Latency:     {res['context_prep_sec']}s")
        print(f"  * 3. Prompt Tokens:            {res['prompt_tokens']}")
        print(f"  * 4. TTFT / Prefill Latency:   {res['ttft_prefill_sec']}s")
        print(f"  * 5. Decode/Gen Latency:       {res['decode_gen_sec']}s (Chat Total: {res['chat_duration_sec']}s)")
        print(f"  * 6. Total Latency:            {res['total_latency_sec']}s")
        print(f"  * 7. Output Token Count:       {res['completion_tokens']} (Finish: {res['finish_reason']})")
        print(f"  * Accuracy Check:              {'PASS' if res['pass'] else 'FAIL'}")
        print(f"  * Answer Preview:\n    " + res['answer'].replace('\n', '\n    '))
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    pos_res = [r for r in results if r["chunks_count"] > 0]
    avg_total = sum(r["total_latency_sec"] for r in results) / len(results)
    avg_prefill = sum(r["ttft_prefill_sec"] for r in pos_res) / len(pos_res) if pos_res else 0
    avg_decode = sum(r["decode_gen_sec"] for r in pos_res) / len(pos_res) if pos_res else 0
    avg_prompt_tok = sum(r["prompt_tokens"] for r in pos_res) / len(pos_res) if pos_res else 0
    avg_out_tok = sum(r["completion_tokens"] for r in pos_res) / len(pos_res) if pos_res else 0
    
    print(f"Average Total Latency:       {avg_total:.2f}s")
    print(f"Average Prompt Tokens:       {avg_prompt_tok:.1f}")
    print(f"Average TTFT/Prefill:        {avg_prefill:.2f}s")
    print(f"Average Decode Generation:   {avg_decode:.2f}s")
    print(f"Average Output Tokens:       {avg_out_tok:.1f}")
    print(f"Accuracy:                    {sum(1 for r in results if r['pass'])}/{len(results)} PASS")

if __name__ == "__main__":
    main()
