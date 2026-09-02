"""
scratch/test_score_gap_policy.py
Score-gap tabanlı dinamik chunk filtreleme politikasını test eder.
"""
import sys

sys.path.insert(0, r"c:\Projects\local-rag-project")

from rag.pipeline import RAGPipeline

def filter_chunks_by_score_gap(chunks: list[dict], min_relative_ratio: float = 0.70, absolute_high_threshold: float = 0.50) -> list[dict]:
    """
    Score-gap tabanlı güvenli context eleme.
    - Top-1 her zaman korunur.
    - Top-2: Eğer skoru >= absolute_high_threshold (0.50) ise VEYA Top-1'e göre oranı >= min_relative_ratio (0.70) ise tutulur.
    - Aksi halde elenir (gereksiz context ve CPU prefill yükü önlenir).
    """
    if len(chunks) <= 1:
        return chunks
    
    top1_score = chunks[0]["score"]
    kept_chunks = [chunks[0]]
    
    for c in chunks[1:]:
        c_score = c["score"]
        ratio = c_score / top1_score if top1_score > 0 else 0
        if c_score >= absolute_high_threshold or ratio >= min_relative_ratio:
            kept_chunks.append(c)
            
    return kept_chunks

def main():
    p = RAGPipeline()
    p.load()
    
    queries = [
        ("Q1_PASSWORD", "Kullanıcı girişinde şifre kuralları ve hatalı denemede hesap bloke süreleri nelerdir?"),
        ("Q2_API_LIMITS", "API istek sınırları ve rate limiting kuralları nelerdir?"),
        ("Q3_BRAND_COLOR", "Mobil tasarım kılavuzuna göre birincil marka rengi ve ikincil vurgu rengi nedir?"),
        ("Q_MULTIDOC", "Mobil tasarım kılavuzundaki renkler ile API güvenlik kuralları nelerdir?"),
        ("Q_JWT", "Access token hangi algoritmayla imzalanıyor?"),
        ("Q4_NEGATIVE", "PostgreSQL veritabanı replikasyon ve failover ayarları nasıl yapılır?"),
    ]
    
    print(f"{'QID':<15} | {'Raw Chunks':<10} | {'Filtered':<10} | {'Top-1 Score':<12} | {'Top-2 Score / Ratio':<20} | {'Karar'}")
    print("-" * 80)
    
    for qid, q in queries:
        raw_chunks = p._retriever.get_top_chunks(q, top_k=2)
        filtered = filter_chunks_by_score_gap(raw_chunks)
        
        top1_s = f"{raw_chunks[0]['score']:.4f}" if raw_chunks else "N/A"
        if len(raw_chunks) >= 2:
            top2_s = f"{raw_chunks[1]['score']:.4f} (r={raw_chunks[1]['score']/raw_chunks[0]['score']:.2f})"
        else:
            top2_s = "N/A"
            
        decision = f"{len(raw_chunks)} -> {len(filtered)} chunk"
        if len(raw_chunks) > len(filtered):
            decision += " (GÜRÜLTÜ ELENDİ!)"
        elif len(raw_chunks) == len(filtered) and len(raw_chunks) > 1:
            decision += " (MULTIDOC KORUNDU)"
            
        print(f"{qid:<15} | {len(raw_chunks):<10} | {len(filtered):<10} | {top1_s:<12} | {top2_s:<20} | {decision}")

if __name__ == "__main__":
    main()
