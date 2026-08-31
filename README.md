# Local RAG — Kurumsal Şartname ve Proje Asistanı

Tamamen çevrimdışı (offline/on-device) çalışan, Microsoft Foundry Local tabanlı yerel PRD, UI/UX Şartnamesi ve Yazılım Analiz Asistanı.  
Gizli kurumsal proje dokümanlarınıza soru sorun — sıfır veri sızıntısı, internet bağlantısı gerekmez.

---

## Gereksinimler

- Python 3.10+
- [Microsoft Foundry Local](https://github.com/microsoft/Foundry-Local) (kurulu olmalı)
- Windows / macOS / Linux

---

## Kurulum

```bash
# 1. Sanal ortam oluştur ve aktive et
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 2. Bağımlılıkları yükle
pip install -r requirements.txt
```

---

## Kullanım

### Adım 1: Belgelerinizi ekleyin

`docs/knowledge_base/` klasörüne `.txt`, `.md` veya `.pdf` dosyalarınızı koyun.

### Adım 2: Belgeleri yükleyin (Ingestion)

```bash
python ingest.py                       # knowledge_base/ klasörünü tara
python ingest.py docs/sample_docs/    # Örnek belgelerle test et
python ingest.py path/to/file.pdf     # Tek dosya
```

### Adım 3: Uygulamayı başlatın

```bash
python main.py           # Streamlit web arayüzü (varsayılan)
python main.py --ui cli  # Terminal arayüzü
```

Streamlit arayüzü için tarayıcınızda http://localhost:8501 açılacaktır.

---

## Proje Yapısı

```
local-rag-project/
├── main.py              # Ana giriş noktası
├── ingest.py            # Belge yükleme scripti
├── config.py            # Yapılandırma sabitleri
├── requirements.txt     # Bağımlılıklar
│
├── rag/                 # RAG pipeline bileşenleri
│   ├── embedder.py      # Embedding model wrapper
│   ├── retriever.py     # Cosine similarity arama
│   ├── generator.py     # LLM cevap üretici
│   └── pipeline.py      # Pipeline orkestrasyon
│
├── db/                  # SQLite veritabanı katmanı
│   ├── schema.py        # Tablo tanımları
│   └── manager.py       # CRUD işlemleri
│
├── ui/                  # Kullanıcı arayüzleri
│   ├── app.py           # Streamlit web UI
│   └── cli.py           # Terminal UI
│
├── docs/
│   ├── knowledge_base/  # Kullanıcı belgeleri (buraya koy)
│   └── sample_docs/     # Örnek/test belgeleri
│
└── tests/               # Unit testler
    └── test_chunker.py
```

---

## Testler

```bash
# Chunker unit testleri (model gerektirmez)
python -m pytest tests/ -v
```

---

## Desteklenen Formatlar

| Format | Uzantı |
|--------|--------|
| Düz metin | `.txt` |
| Markdown | `.md` |
| PDF | `.pdf` |

---

## Mimari

```
[Kullanıcı Sorusu]
       ↓
  [Embedder] — qwen3-embedding-0.6b
       ↓
  [Retriever] — Cosine Similarity, Top-K
       ↓ (ilgili chunk'lar)
  [Generator] — phi-3.5-mini
       ↓
  [Cevap + Kaynaklar]
```

Tüm işlemler yereldir. Hiçbir veri dışarı çıkmaz.

---

## Yapılandırma

`config.py` dosyasından şunları özelleştirebilirsin:

| Ayar | Varsayılan | Açıklama |
|------|------------|----------|
| `LLM_MODEL_ALIAS` | `phi-3.5-mini` | Chat modeli |
| `EMBEDDING_MODEL_ALIAS` | `qwen3-embedding-0.6b` | Embedding modeli |
| `TOP_K_CHUNKS` | `3` | Her sorgu için getirilen chunk sayısı |
| `CHUNK_MIN_CHARS` | `50` | Minimum chunk boyutu |
| `CHUNK_MAX_CHARS` | `800` | Maksimum chunk boyutu |
