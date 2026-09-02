import sys
sys.path.insert(0, r"c:\Projects\local-rag-project")
from rag.pipeline import RAGPipeline

p = RAGPipeline()
p.load()

queries = [
    "Kullanıcı girişinde şifre kuralları ve hatalı denemede hesap bloke süreleri nelerdir?",
    "API istek sınırları ve rate limiting kuralları nelerdir?",
    "Mobil tasarım kılavuzuna göre birincil marka rengi ve ikincil vurgu rengi nedir?",
]

for q in queries:
    chunks = p._retriever.get_top_chunks(q)
    print(f"\n==========================================")
    print(f"QUERY: {q}")
    print(f"==========================================")
    for i, c in enumerate(chunks, 1):
        print(f"--- Chunk {i} | Source: {c['source_name']} | Score: {c['score']:.4f} | Dense: {c['dense_score']:.4f} | Lexical: {c['lexical_score']:.4f} | Chars: {len(c['content'])} ---")
        print(c['content'])
