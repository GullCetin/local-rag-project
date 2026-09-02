"""
config.py — Local RAG AI Assistant Configuration
=================================================
Tüm yapılandırma sabitleri burada merkezi olarak tutulur.
Değiştirmek istediğin ayarları buradan düzenle.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# SQLite veritabanı dosyasının konumu
DB_PATH = os.path.join(BASE_DIR, "data", "rag_store.db")

# Kullanıcının belgelerini koyacağı klasör
KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "docs", "knowledge_base")

# Örnek/test belgeleri
SAMPLE_DOCS_DIR = os.path.join(BASE_DIR, "docs", "sample_docs")

# ---------------------------------------------------------------------------
# Model Configuration
# ---------------------------------------------------------------------------
# Kullanılabilir LLM modelleri (küçükten büyüğe, en hızlıdan yavaşa)
# qwen3-1.7b  : ~1.4GB, ~8-15sn, hafif cevaplar
# qwen3-4b    : ~2.8GB, ~20-35sn, dengeli
# phi-3.5-mini: ~2.6GB, ~30-60sn, çok yönlü
AVAILABLE_LLM_MODELS = [
    ("qwen3-1.7b",   "Qwen3-1.7B"),
    ("qwen3-4b",     "Qwen3-4B"),
    ("phi-3.5-mini", "Phi-3.5-mini"),
]

# Aktif LLM model alias  — AVAILABLE_LLM_MODELS listesindeki alias'lardan biri olmalı
LLM_MODEL_ALIAS = "phi-3.5-mini"
EMBEDDING_MODEL_ALIAS = "qwen3-embedding-0.6b"

# Foundry Local uygulaması adı (SDK loglama için)
APP_NAME = "local-rag-assistant"

# ---------------------------------------------------------------------------
# Supported Document Formats & Filtering (rules.txt: Adım 1 - Bilgi Envanteri)
# ---------------------------------------------------------------------------
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}

# RAG bilgi hattına girmemesi gereken çöp, lisans ve hassas dosya kalıpları
IGNORED_FILE_PATTERNS = [
    r"^notice(\.txt)?$",
    r"^license(\.txt)?$",
    r"^.*apikey.*$",
    r"^.*secret.*$",
    r"^.*\.removed$",
    r"^.*\.tmp$",
    r"^.*\.log$",
]

# Ingestion'da kabul edilecek maksimum dosya boyutu (MB)
MAX_INGEST_FILE_SIZE_MB = 2.0

# Tek bir dosyadan üretilecek maksimum chunk sayısı
MAX_CHUNKS_PER_FILE = 200

# ---------------------------------------------------------------------------
# Chunking Configuration (rules.txt: Adım 5 - Bağlam Bütünlüğü)
# ---------------------------------------------------------------------------
# Bir chunk'ın minimum karakter sayısı (çok kısa gürültüleri filtreler)
CHUNK_MIN_CHARS = 50

# Bir chunk'ın maximum karakter sayısı (bağlamı koparmadan bölmek için)
CHUNK_MAX_CHARS = 1000

# Paragraflar veya alt parçalar arası örtüşme (overlap) karakter sayısı
# rules.txt Adım 5: Bağlam kopmasını azaltmak için daha büyük overlap
CHUNK_OVERLAP_CHARS = 120

# ---------------------------------------------------------------------------
# Retrieval Configuration (rules.txt: Adım 8 - Retrieval Tasarımı)
# ---------------------------------------------------------------------------
# Her sorgu için en odaklı kaç chunk getirilsin?
# top_k=2: Ablasyon benchmarkında optimum hız (TTFT ~12s) ve tam doğruluk dengesi
TOP_K_CHUNKS = 2

# Hibrit Arama Ağırlıkları: Dense (Semantik) + Lexical (Sözcük/Başlık)
# Türkçe için semantik biraz daha ağır; rules.txt Adım 6 & 8
HYBRID_DENSE_WEIGHT = 0.65
HYBRID_LEXICAL_WEIGHT = 0.35

# Cosine similarity / Hibrit skor filtre eşiği (alakasız belgeleri eler)
# 0.32: Negatif sorgu sızıntılarını (0.29) %100 engeller, pozitif Top-1/Top-2 kapsamını korur
SCORE_THRESHOLD = 0.32

# ---------------------------------------------------------------------------
# LLM Generation Parameters (rules.txt: Adım 9 - Modelin Sınırlarını Yönetmek)
# ---------------------------------------------------------------------------
LLM_TEMPERATURE = 0.1
LLM_TOP_P = 0.9
# rules.txt Adım 9: 512 çok kısa, cevaplar kesiliyor → 1024'e çıkarıldı
LLM_MAX_TOKENS = 1024
LLM_FREQUENCY_PENALTY = 0.3
LLM_PRESENCE_PENALTY = 0.1

# ---------------------------------------------------------------------------
# LLM System Prompt (rules.txt: Adım 0 ve Adım 9 - Grounded Generation)
# ---------------------------------------------------------------------------
# rules.txt Adım 9: Kesin kaynak dayanaklı üretim — uydurma yok, kaynak dayanaklı
SYSTEM_PROMPT = """\
Sen kurumsal belgelere dayalı, güvenilir bir Türkçe soru-cevap asistanısın.

Temel kurallar:
1. YALNIZCA verilen kaynak belgelerindeki bilgileri kullan. Dış bilgin varsa onu kullanma.
2. Belgede yoksa: "Verilen belgelerde bu konuda bilgi yer almamaktadır." yaz ve dur.
3. Cevabı doğrudan ver. "Elbette", "Tabii ki", "Merhaba" gibi giriş ifadeleri yazma.
4. ÖZLÜLÜK: Basit olgusal sorulara (renk, sayı, isim, tarih gibi) TEK CÜMLE veya madde ile cevap ver. Gereksiz açıklama ekleme.
5. Karmaşık sorularda madde madde veya adım adım anlat.
6. Kaynaklarda çelişen bilgi varsa, her iki kaynağı da belirt.
7. Cevabını bitirince dur. Tekrar etme, yorum ekleme.
"""


# Sorgu yeniden yazma şablonu (konuşma geçmişi için)
QUERY_REWRITE_PROMPT = """\
Aşağıdaki sohbet geçmişini ve kullanıcının son sorusunu incele.
Kullanıcının son sorusu önceki konuşmaya atıfta bulunuyorsa (ör. 'bunu açıkla', 'neden peki'), belge veritabanında semantik ve kelime araması yapmaya uygun, tek başına anlamlı, kısa bir Türkçe arama sorgusuna dönüştür.
Eğer soru zaten bağımsızsa, aynen döndür.
SADECE yeni arama sorgusunu yaz, hiçbir açıklama ekleme.
"""

# ---------------------------------------------------------------------------
# UI Configuration (rules.txt: Adım 10 - İzleme ve Bakım)
# ---------------------------------------------------------------------------
APP_TITLE = "Local RAG AI Assistant"
APP_DESCRIPTION = "Kurumsal Düzeyde Güvenilir Belge Soru-Cevap Sistemi (100% Yerel & Çevrimdışı)"
