"""
scratch/audit_and_token_breakdown.py
Bölüm 1: Token Breakdown (System Prompt vs Query vs RAG Context)
Bölüm 3: Model / Hardware Configuration Audit
Bölüm 4: Score-Gap Dağılım Raporu
"""
import sys
import os
import time
import json
import inspect

sys.path.insert(0, r"c:\Projects\local-rag-project")

from rag.pipeline import RAGPipeline
from rag.generator import GENERATOR_SYSTEM_PROMPT
from config import LLM_MODEL_ALIAS, APP_NAME

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

def audit_hardware_and_model(pipeline):
    print("=" * 80)
    print("BÖLÜM 3: MODEL & HARDWARE CONFIGURATION AUDIT")
    print("=" * 80)
    
    g = pipeline._generator
    client = g._chat_client
    model = g._model
    
    print(f"Model Alias:             {LLM_MODEL_ALIAS}")
    print(f"Model Object:            {model}")
    print(f"Model Type:              {type(model)}")
    
    # Model attributes
    for attr in ["id", "name", "alias", "description", "is_cached", "device", "backend", "quantization", "threads", "context_length"]:
        if hasattr(model, attr):
            print(f"  model.{attr}: {getattr(model, attr)}")
            
    # Model catalog details
    try:
        from foundry_local_sdk import FoundryLocalManager
        mgr = FoundryLocalManager.instance
        catalog_model = mgr.catalog.get_model(LLM_MODEL_ALIAS)
        print(f"Catalog Model Info:")
        for attr in dir(catalog_model):
            if not attr.startswith("_") and not callable(getattr(catalog_model, attr)):
                print(f"  catalog.{attr}: {getattr(catalog_model, attr)}")
    except Exception as e:
        print(f"  Error reading catalog: {e}")
        
    print(f"\nChatClient Type:         {type(client)}")
    if hasattr(client, "settings"):
        s = client.settings
        print(f"ChatClient Settings:")
        for attr in dir(s):
            if not attr.startswith("_") and not callable(getattr(s, attr)):
                print(f"  settings.{attr}: {getattr(s, attr)}")

def measure_token_breakdown(pipeline):
    print("\n" + "=" * 80)
    print("BÖLÜM 1 & 4: TOKEN BREAKDOWN & SCORE-GAP DAĞILIMI")
    print("=" * 80)
    
    client = pipeline._generator._chat_client
    
    # 1. System Prompt Token Count
    sys_msgs = [{"role": "system", "content": GENERATOR_SYSTEM_PROMPT}, {"role": "user", "content": "test"}]
    pipeline._generator._apply_generation_settings(max_tokens=1)
    resp = client.complete_chat(messages=sys_msgs)
    sys_plus_dummy = resp.usage.prompt_tokens if resp and resp.usage else 0
    
    # Dummy user message token count
    dummy_msgs = [{"role": "user", "content": "test"}]
    resp_dummy = client.complete_chat(messages=dummy_msgs)
    dummy_tokens = resp_dummy.usage.prompt_tokens if resp_dummy and resp_dummy.usage else 0
    
    sys_tokens = sys_plus_dummy - dummy_tokens
    print(f"System Prompt Token Sayısı: ~{sys_tokens} token (Chars: {len(GENERATOR_SYSTEM_PROMPT)})")
    
    print("\n" + "-" * 80)
    print(f"{'QID':<15} | {'Raw K':<6} | {'Gap K':<6} | {'Top1 Scr':<9} | {'Top2 Scr':<9} | {'Ratio':<6} | {'SysTok':<7} | {'QryTok':<7} | {'CtxTok':<7} | {'TotPrompt':<10} | {'TTFT':<7} | {'Decode':<7} | {'Total':<7} | {'OutTok'}")
    print("-" * 80)
    
    for item in QUESTIONS:
        qid = item["id"]
        q = item["question"]
        
        # Retrieval
        t_start = time.perf_counter()
        t_ret0 = time.perf_counter()
        raw_chunks = pipeline._retriever.get_top_chunks(q, top_k=2)
        t_ret = time.perf_counter() - t_ret0
        
        if not raw_chunks:
            print(f"{qid:<15} | {0:<6} | {0:<6} | {'N/A':<9} | {'N/A':<9} | {'N/A':<6} | {0:<7} | {0:<7} | {0:<7} | {0:<10} | {'0.0s':<7} | {'0.0s':<7} | {t_ret:<6.2f}s | 0 (BYPASS)")
            continue
            
        top1_score = raw_chunks[0]["score"]
        top2_score = raw_chunks[1]["score"] if len(raw_chunks) > 1 else None
        ratio = (top2_score / top1_score) if top2_score is not None else None
        
        # Context preparation (with current score-gap filter in place)
        context = pipeline._retriever.format_context(raw_chunks)
        
        # Measure Query-only tokens
        q_msgs = [{"role": "user", "content": f"SORU: {q}"}]
        resp_q = client.complete_chat(messages=q_msgs)
        q_tokens = resp_q.usage.prompt_tokens if resp_q and resp_q.usage else 0
        
        # Generation
        ans = pipeline._generator.generate(q, context)
        metrics = getattr(pipeline._generator, "last_metrics", {})
        
        tok_usage = metrics.get("token_usage", {})
        total_prompt_tok = tok_usage.get("prompt_tokens", 0)
        out_tok = tok_usage.get("completion_tokens", 0)
        ttft = metrics.get("ttft_sec", 0.0)
        chat_dur = metrics.get("chat_duration_sec", 0.0)
        decode_time = max(0.0, chat_dur - ttft)
        t_total = time.perf_counter() - t_start
        
        # Context tokens calculation
        ctx_tokens = max(0, total_prompt_tok - sys_tokens - q_tokens)
        
        top2_str = f"{top2_score:.4f}" if top2_score is not None else "-"
        ratio_str = f"{ratio:.2f}" if ratio is not None else "-"
        
        print(f"{qid:<15} | {len(raw_chunks):<6} | {metrics.get('context_char_count') and len(raw_chunks):<6} | {top1_score:<9.4f} | {top2_str:<9} | {ratio_str:<6} | {sys_tokens:<7} | {q_tokens:<7} | {ctx_tokens:<7} | {total_prompt_tok:<10} | {ttft:<6.2f}s | {decode_time:<6.2f}s | {t_total:<6.2f}s | {out_tok}")

def main():
    p = RAGPipeline()
    p.load()
    audit_hardware_and_model(p)
    measure_token_breakdown(p)

if __name__ == "__main__":
    main()
