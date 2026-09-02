"""
scratch/test_context_trimming.py
Context trimming ve contamination engelleme prototipini test eder.
"""
import sys
import re

sys.path.insert(0, r"c:\Projects\local-rag-project")

from rag.pipeline import RAGPipeline
from rag.retriever import calculate_lexical_score

def trim_chunk_content(query: str, content: str) -> str:
    """
    Chunk içerisindeki maddeleri/satırları inceler.
    Eğer chunk açık madde işaretli bir listeyse ve bazı maddeler tamamen alakasızsa:
    Sadece sorgu ile ilişkili maddeleri (başlığı ve sayısal değerleriyle) korur.
    Bağlamı bozmamak için paragraf metinlerine dokunmaz, sadece bağımsız madde listelerinde çalışır.
    """
    lines = content.strip().split("\n")
    # Eğer maddeli liste değilse (örn. düz paragraf), aynen bırak
    bullet_lines = [l for l in lines if re.match(r"^\s*[-*•\d+.]\s+", l)]
    if len(bullet_lines) < 2:
        return content
        
    query_words = set(re.findall(r"\b[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]+\b", query.lower()))
    stop_words = {"ve", "ile", "bir", "mi", "mı", "bu", "şu", "için", "ne", "nedir", "nelerdir", "neler", "göre", "kadar"}
    keywords = query_words - stop_words
    
    kept_lines = []
    header_lines = []
    
    for line in lines:
        raw_l = line.strip()
        # Başlık satırları (örn. [Belge: ...] veya Konu: ...)
        if not re.match(r"^\s*[-*•\d+.]\s+", line) and not raw_l.startswith("-"):
            header_lines.append(line)
            continue
            
        # Madde satırı: sorgu kelimelerinden herhangi birini içeriyor mu?
        line_words = set(re.findall(r"\b[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]+\b", raw_l.lower()))
        matched = line_words.intersection(keywords)
        
        # Eğer eşleşme varsa veya satır çok genel değilse tut
        if matched:
            kept_lines.append(line)
            
    # Eğer hiçbir madde eşleşmediyse (güvenlik fallback'i), orijinal content'i dön
    if not kept_lines:
        return content
        
    # Başlıklar + Seçilen maddeler
    res = []
    if header_lines:
        res.extend(header_lines)
    res.extend(kept_lines)
    return "\n".join(res)

def main():
    p = RAGPipeline()
    p.load()
    
    q1 = "Kullanıcı girişinde şifre kuralları ve hatalı denemede hesap bloke süreleri nelerdir?"
    chunks = p._retriever.get_top_chunks(q1, top_k=1)
    orig_content = chunks[0]["content"]
    trimmed_content = trim_chunk_content(q1, orig_content)
    
    print("=== Q1 ORIGINAL CHUNK CONTENT ===")
    print(orig_content)
    print("\n=== Q1 TRIMMED CHUNK CONTENT ===")
    print(trimmed_content)
    print(f"\nOriginal Chars: {len(orig_content)} | Trimmed Chars: {len(trimmed_content)} (Tasarruf: {len(orig_content) - len(trimmed_content)} chars)")

if __name__ == "__main__":
    main()
