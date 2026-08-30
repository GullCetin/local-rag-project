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
# Chunking Configuration
# ---------------------------------------------------------------------------
# Bir chunk'ın minimum karakter sayısı (çok kısa chunk'ları filtreler)
CHUNK_MIN_CHARS = 50

# Bir chunk'ın maximum karakter sayısı (çok uzun chunk'ları böler)
CHUNK_MAX_CHARS = 800

# ---------------------------------------------------------------------------
# Retrieval Configuration
# ---------------------------------------------------------------------------
# Her sorgu için kaç chunk getirilsin? (Daha zengin bağlam için 4'e çıkarıldı)
TOP_K_CHUNKS = 4

# ---------------------------------------------------------------------------
# LLM Generation Parameters (Anti-repetition & quality tuning)
# ---------------------------------------------------------------------------
LLM_TEMPERATURE = 0.1
LLM_TOP_P = 0.9
LLM_MAX_TOKENS = 450
LLM_FREQUENCY_PENALTY = 0.5   # Repetition prevention
LLM_PRESENCE_PENALTY = 0.2    # Topic progress & diversity
SYSTEM_PROMPT = """\
# ROL VE TEMEL GÖREV
Sen, bir Retrieval-Augmented Generation (RAG) sisteminin **Grounded Answer Generation Agent**'ısın.
Görevin: Kullanıcı sorusuna YALNIZCA sana sağlanan <belge> alıntılarını temel alarak en doğru, açık, mantıklı ve doğrudan cevabı vermektir.

# TEMEL ÇALIŞMA KURALLARI (MUTLAK KURAL):
1. **Source of Truth (Tek Gerçek Kaynağı):**
   - Sana verilen <belge> alıntıları tek bilgi kaynağındır.
   - Belgelerde bulunmayan hiçbir olguyu, sayıyı, tarihi, ismi, kodu veya özelliği UYDURMA (Zero Hallucination).
   - Bir aracın/SDK'nın adını veya detayını, sorulan ana kavramın tanımıymış gibi sunma (Noise Elimination).

2. **Inference vs Invention (Çıkarım vs Uydurma):**
   - Belgelerdeki doğrudan ifadeleri (Level 1) ve açık mantıksal sonuçları (Level 2) birleştirerek akıcı bir yanıt oluşturabilirsin.
   - Ancak belgede olmayan harici varsayımları (Level 3) gerçek gibi sunma.

3. **Cevap Yapısı & Doğallık:**
   - Sorulan soruya doğrudan, net, profesyonel ve zengin bir Türkçe ile cevap ver.
   - Soru bir kavramın tanımını istiyorsa (örn. "X nedir?"), belgedeki temel tanımından, özelliklerinden ve kullanım alanlarından sentez yaparak açıkla.
   - Cevabının içine gereksiz teknik skorlar, prompt etiketleri veya iç düşünceler yazma.

4. **Yetersiz Bilgi Durumu:**
   - Eğer kullanıcının sorusu sağlanan belgelerle tamamen cevapsız kalıyorsa: "Sağlanan kaynak dokümanlarda bu konuda yeterli bilgi bulunmamaktadır." de.
   - Eğer kısmen cevaplanabiliyorsa: Bilinen kısmı açıkla, bilinmeyen kısmın dokümanda yer almadığını belirt.
"""

# Sohbet geçmişi olan takip sorularını bağımsız arama sorgusuna dönüştürme şablonu
QUERY_REWRITE_PROMPT = """\
Aşağıdaki sohbet geçmişini ve kullanıcının son sorusunu incele.
Kullanıcının son sorusu önceki konuşmaya atıfta bulunuyorsa (örneğin "detaylandır", "bunu açıkla", "örnek ver", "neden"), belge veritabanında semantik arama yapmaya uygun, tek başına anlamlı, kısa ve net bir arama sorgusuna dönüştür.
Eğer kullanıcının sorusu zaten bağımsız ve net bir soruysa, soruyu değiştirmeden aynen döndür.

SADECE ve YALNIZCA yeni arama sorgusunu yaz, başına/sonuna açıklama ekleme.
"""

# ---------------------------------------------------------------------------
# Supported Document Formats
# ---------------------------------------------------------------------------
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}

# ---------------------------------------------------------------------------
# Retrieval Quality Threshold
# ---------------------------------------------------------------------------
# Cosine similarity skoru bu değerin altındaki chunk'lar LLM'e verilmez.
# 0.0 = hiç filtreleme yok, 1.0 = sadece mükemmel eşleşmeler
# Tavsiye: 0.25 - 0.35 arası (model ve veri setine göre ayarla)
SCORE_THRESHOLD = 0.25

# ---------------------------------------------------------------------------
# UI Configuration
# ---------------------------------------------------------------------------
APP_TITLE = "Local RAG AI Assistant"
APP_DESCRIPTION = "Ask questions about your documents — 100% offline, powered by Foundry Local"
