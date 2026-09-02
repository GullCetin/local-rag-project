import sys
sys.path.insert(0, r"c:\Projects\local-rag-project")
from rag.pipeline import RAGPipeline
import re

p = RAGPipeline()
p.load()

for q in ["Mobil tasarım kılavuzuna göre birincil marka rengi ve ikincil vurgu rengi nedir?", "API istek sınırları ve rate limiting kuralları nelerdir?"]:
    chunks = p._retriever.get_top_chunks(q)
    raw_ctx = p._retriever.format_context(chunks)
    
    # Cleaned context (strip multiple whitespaces/newlines)
    clean_ctx = re.sub(r'[ \t]+', ' ', raw_ctx)
    clean_ctx = re.sub(r'\n{3,}', '\n\n', clean_ctx).strip()
    
    print(f"=== {q} ===")
    print(f"Raw context chars: {len(raw_ctx)}")
    print(f"Clean context chars: {len(clean_ctx)}")
