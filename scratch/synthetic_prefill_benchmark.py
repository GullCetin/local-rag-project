"""
scratch/synthetic_prefill_benchmark.py
Sentetik Prefill Benchmark: 100, 200, 400, 600, 800, 1000 tokenlık promptlarda TTFT ve Decode sürelerini ölçer.
En az 3 tekrar yaparak ortalama değerleri hesaplar.
"""
import sys
import time

sys.path.insert(0, r"c:\Projects\local-rag-project")

from rag.generator import Generator

TARGET_TOKEN_SIZES = [100, 200, 400, 600, 800, 1000]
NUM_RUNS = 3

# Sentetik dolgu metni (Türkçe ve İngilizce dengeli kelimeler)
FILLER_SENTENCE = "Bu bir sentetik performans test cümlesidir ve modelin bağlam işleme hızını ölçmektedir. "

def build_prompt_with_approx_tokens(client, target_tokens: int) -> tuple[list[dict], int]:
    """
    Belirli hedef token sayısına ulaşana kadar kullanıcı mesajına dolgu ekler.
    """
    # Taban sistem mesajı ve kullanıcı talimatı (kısa cevap üretmesi için)
    sys_msg = "Sen bir test asistanısın. Kullanıcının sorusuna yalnızca tek bir kelime ile 'Tamam' de."
    
    # İkili arama / iteratif yaklaşımla tam token sayısını bul
    low_repeat = 1
    high_repeat = max(2, target_tokens // 4)
    best_msgs = []
    best_tokens = 0
    
    # Yaklaşık olarak hedefi bulalım
    for repeat in range(1, 300):
        filler = FILLER_SENTENCE * repeat
        user_content = f"Metin: {filler}\n\nLütfen yalnızca 'Tamam' yaz."
        msgs = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_content}
        ]
        resp = client.complete_chat(messages=msgs)
        current_tokens = resp.usage.prompt_tokens if resp and resp.usage else 0
        best_msgs = msgs
        best_tokens = current_tokens
        if current_tokens >= target_tokens:
            break
            
    return best_msgs, best_tokens

def main():
    print("=" * 80)
    print(f"SENTETİK PREFILL BENCHMARK ({NUM_RUNS} Tekrar)")
    print("=" * 80)
    
    g = Generator()
    g.load()
    client = g._chat_client
    
    results = []
    
    for target in TARGET_TOKEN_SIZES:
        print(f"\nHedef Token Boyutu: {target} token...")
        messages, actual_tokens = build_prompt_with_approx_tokens(client, target)
        print(f"  Oluşturulan Prompt Tokens: {actual_tokens}")
        
        runs_ttft = []
        runs_decode = []
        runs_total = []
        runs_out_tokens = []
        
        for run_idx in range(NUM_RUNS):
            g._apply_generation_settings(max_tokens=10)
            
            t0 = time.perf_counter()
            ttft = None
            out_text = ""
            tokens_generated = 0
            
            stream = client.complete_streaming_chat(messages=messages)
            for chunk in stream:
                if hasattr(chunk, "choices") and chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    content = getattr(delta, "content", "") or ""
                    if content:
                        if ttft is None:
                            ttft = time.perf_counter() - t0
                        out_text += content
                        tokens_generated += 1
                        
            t_total = time.perf_counter() - t0
            ttft_val = ttft if ttft is not None else t_total
            decode_val = max(0.0, t_total - ttft_val)
            
            runs_ttft.append(ttft_val)
            runs_decode.append(decode_val)
            runs_total.append(t_total)
            runs_out_tokens.append(tokens_generated)
            print(f"    Run {run_idx+1}: TTFT={ttft_val:.3f}s | Decode={decode_val:.3f}s | Total={t_total:.3f}s | OutToks={tokens_generated} | Text='{out_text.strip()}'")
            
        avg_ttft = sum(runs_ttft) / len(runs_ttft)
        avg_decode = sum(runs_decode) / len(runs_decode)
        avg_total = sum(runs_total) / len(runs_total)
        avg_out = sum(runs_out_tokens) / len(runs_out_tokens)
        ms_per_prompt_token = (avg_ttft * 1000) / actual_tokens
        
        results.append({
            "target": target,
            "actual_tokens": actual_tokens,
            "avg_ttft": avg_ttft,
            "avg_decode": avg_decode,
            "avg_total": avg_total,
            "avg_out": avg_out,
            "ms_per_prompt_token": ms_per_prompt_token,
        })
        
    print("\n" + "=" * 80)
    print("SENTETİK PREFILL BENCHMARK ÖZET TABLOSU")
    print("=" * 80)
    print(f"{'Prompt Tokens':<15} | {'Ortalama TTFT (s)':<18} | {'Ortalama Decode (s)':<20} | {'Ortalama Total (s)':<18} | {'ms / Prompt Token'}")
    print("-" * 80)
    for r in results:
        print(f"{r['actual_tokens']:<15} | {r['avg_ttft']:<18.3f} | {r['avg_decode']:<20.3f} | {r['avg_total']:<18.3f} | {r['ms_per_prompt_token']:<15.2f} ms")

if __name__ == "__main__":
    main()
