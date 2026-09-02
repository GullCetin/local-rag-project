import sys
sys.path.insert(0, r"c:\Projects\local-rag-project")
from rag.pipeline import RAGPipeline
from db.manager import get_all_chunks

p = RAGPipeline()
p.load()

# Test set of queries (Single doc + Multi doc + Negative)
test_queries = [
    # Single doc queries
    "Kullanıcı girişinde şifre kuralları ve hatalı denemede hesap bloke süreleri nelerdir?",
    "API istek sınırları ve rate limiting kuralları nelerdir?",
    "Mobil tasarım kılavuzuna göre birincil marka rengi ve ikincil vurgu rengi nedir?",
    "Access token hangi algoritmayla imzalanıyor?",
    "Veritabanında hangi tablolar bulunmaktadır?",
    # Multi-doc queries (cross-document)
    "Sistem mimarisi ve güvenlik politikaları hakkında bilgi verin.",
    "Mobil tasarım kılavuzundaki renkler ile API güvenlik kuralları nelerdir?",
    # Negative queries
    "PostgreSQL veritabanı replikasyon ve failover ayarları nasıl yapılır?",
    "Kuantum şifreleme anahtarları nasıl üretilir?",
]

print("=== RETRIEVAL SCORE GAP ANALYSIS ===")
for q in test_queries:
    chunks = p._retriever.get_top_chunks(q, top_k=4)
    print(f"\nQ: {q}")
    if not chunks:
        print("  -> No chunks passed threshold (Negative Bypass)")
        continue
    top1_score = chunks[0]["score"]
    for i, c in enumerate(chunks, 1):
        ratio = c["score"] / top1_score
        print(f"  Chunk {i}: score={c['score']:.4f} | ratio={ratio:.2f} | source={c['source_name']}")
