"""
scratch/test_streaming_early_stop.py
Streaming ve akıllı erken durma ile latency ölçümü.
"""
import sys
import time
import re

sys.path.insert(0, r"c:\Projects\local-rag-project")

from rag.pipeline import RAGPipeline
from rag.generator import _clean_response, _detect_repetition_loop, GENERATOR_SYSTEM_PROMPT

QUESTIONS = [
    {
        "id": "Q1_PASSWORD",
        "question": "Kullanıcı girişinde şifre kuralları ve hatalı denemede hesap bloke süreleri nelerdir?",
        "expected_facts": ["8", "15"],
        "forbidden_contaminants": ["30 gün", "180 saniye", "OTP"],
    },
    {
        "id": "Q2_API_LIMITS",
        "question": "API istek sınırları ve rate limiting kuralları nelerdir?",
        "expected_facts": ["60", "300"],
        "forbidden_contaminants": [],
    },
    {
        "id": "Q3_BRAND_COLOR",
        "question": "Mobil tasarım kılavuzuna göre birincil marka rengi ve ikincil vurgu rengi nedir?",
        "expected_facts": ["#0E2538", "#2563EB"],
        "forbidden_contaminants": [],
    },
    {
        "id": "Q4_POSTGRES_REFUSAL",
        "question": "PostgreSQL veritabanı replikasyon ve failover ayarları nasıl yapılır?",
        "expected_facts": ["Verilen belgelerde bu bilgi yer almamaktadır."],
        "forbidden_contaminants": [],
    }
]

def generate_streaming(generator, question: str, context: str, token_budget: int):
    prefix = "/no_think\n" if "qwen" in (generator._current_alias or "").lower() else ""
    user_message = (
        f"{prefix}"
        f"BELGELER:\n{context}\n\n"
        f"SORU: {question}"
    )
    messages = [
        {"role": "system", "content": GENERATOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    
    generator._apply_generation_settings(max_tokens=token_budget)
    
    stream = generator._chat_client.complete_streaming_chat(messages=messages)
    
    full_text = ""
    ttft = None
    t0 = time.perf_counter()
    tokens_count = 0
    
    for chunk in stream:
        if hasattr(chunk, "choices") and chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta
            delta_content = delta.content if hasattr(delta, "content") else ""
            if delta_content:
                if ttft is None:
                    ttft = time.perf_counter() - t0
                full_text += delta_content
                tokens_count += 1
                
                # 1. Tekrar döngüsü kontrolü
                is_loop, _ = _detect_repetition_loop(full_text)
                if is_loop:
                    break
                
                # 2. Prompt echo veya gereksiz döngü başlangıcı kontrolü (örn: "\nForm:", "\nKURAL", "\nSAYISAL DOĞRULUK:")
                if len(full_text) > 40:
                    tail = full_text[-50:].lower()
                    if any(stop_pat in tail for stop_pat in ["\nkural ", "\nformat:", "\nsayısal doğruluk:", "\nform:"]):
                        break
    
    gen_time = time.perf_counter() - t0
    clean_ans = _clean_response(full_text)
    
    return clean_ans, gen_time, ttft, tokens_count, full_text

def main():
    p = RAGPipeline()
    p.load()
    
    print("=== STREAMING GENERATION LATENCY BENCHMARK ===")
    
    for item in QUESTIONS:
        qid = item["id"]
        q = item["question"]
        print(f"\n--- [{qid}] {q} ---")
        
        t0 = time.perf_counter()
        chunks = p._retriever.get_top_chunks(q)
        t_ret = time.perf_counter() - t0
        
        if not chunks:
            print(f"Bypassed in {t_ret:.2f}s -> Refusal")
            continue
            
        context = p._retriever.format_context(chunks)
        budget = p._generator._estimate_token_budget(q, context)
        
        ans, t_gen, ttft, tok_count, raw = generate_streaming(p._generator, q, context, budget)
        t_tot = time.perf_counter() - t0
        
        print(f"Total: {t_tot:.2f}s | Ret: {t_ret:.2f}s | TTFT: {ttft or 0:.2f}s | Gen: {t_gen:.2f}s | Toks: {tok_count}")
        print(f"Answer:\n{ans}")
        
        has_expected = all(ef.lower() in ans.lower() for ef in item["expected_facts"])
        has_forbidden = any(fc.lower() in ans.lower() for fc in item["forbidden_contaminants"])
        passed = has_expected and not has_forbidden
        print(f"Accuracy: {'PASS' if passed else 'FAIL'}")

if __name__ == "__main__":
    main()
