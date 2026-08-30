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
    ("qwen3-1.7b",   "Qwen3-1.7B  ⚡ (Hızlı ~8-15sn, 1.4GB)"),
    ("qwen3-4b",     "Qwen3-4B   ⚡⚡ (Dengeli ~20-35sn, 2.8GB)"),
    ("phi-3.5-mini", "Phi-3.5-mini  (Yavaş ~30-60sn, 2.6GB)"),
]

# Aktif LLM model alias  — AVAILABLE_LLM_MODELS listesindeki alias'lardan biri olmalı
LLM_MODEL_ALIAS = "qwen3-1.7b"
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
CHUNK_MAX_CHARS = 800

# Paragraflar veya alt parçalar arası örtüşme (overlap) karakter sayısı
CHUNK_OVERLAP_CHARS = 80

# ---------------------------------------------------------------------------
# Retrieval Configuration (rules.txt: Adım 8 - Retrieval Tasarımı)
# ---------------------------------------------------------------------------
# Her sorgu için en odaklı kaç chunk getirilsin?
# 3 chunk = Tam ve zengin bağlam (giriş cümleleri + maddeler + detaylar)
TOP_K_CHUNKS = 3

# Hibrit Arama Ağırlıkları: Dense (Semantik) + Lexical (Sözcük/Başlık)
HYBRID_DENSE_WEIGHT = 0.60
HYBRID_LEXICAL_WEIGHT = 0.40

# Cosine similarity / Hibrit skor filtre eşiği (alakasız belgeleri eler)
SCORE_THRESHOLD = 0.30

# ---------------------------------------------------------------------------
# LLM Generation Parameters (rules.txt: Adım 9 - Modelin Sınırlarını Yönetmek)
# ---------------------------------------------------------------------------
LLM_TEMPERATURE = 0.1
LLM_TOP_P = 0.9
LLM_MAX_TOKENS = 512
LLM_FREQUENCY_PENALTY = 0.3
LLM_PRESENCE_PENALTY = 0.1

# ---------------------------------------------------------------------------
# LLM System Prompt (rules.txt: Adım 0 ve Adım 9 - Grounded Generation)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
Sen bir Belge Soru-Cevap asistanısın.
Görevin: Verilen KAYNAK BELGELER'deki bilgilere göre kullanıcının sorusunu Türkçe olarak net ve doğrudan yanıtlamaktır.
Kural 1: Yalnızca verilen belgelerdeki bilgileri kullan.
Kural 2: Eğer belgelerde bilgi yoksa "Verilen belgelerde bu bilgi yer almamaktadır." de.
Kural 3: Doğrudan cevabı yaz, gereksiz giriş cümleleri ekleme.
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
