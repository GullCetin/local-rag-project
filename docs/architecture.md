# Local RAG AI Assistant — Sistem Mimarisi Dokümantasyonu

Bu doküman; **Microsoft Foundry Local** üzerinde çalışan, tamamen çevrimdışı (offline/on-device) RAG (*Retrieval-Augmented Generation*) sisteminin katmanlı mimarisini, veri akışını ve kaynak dayanaklılık (*grounding*) prensiplerini açıklamaktadır.

---

## 1. Genel Mimari Şeması

```text
Kullanıcı Sorusu (Streamlit UI / CLI)
         │
         ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 1. Query Reformulation / Rewriter                      │
 │    (Sohbet geçmişini inceleyerek takip sorularını      │
 │     bağımsız, net bir arama sorgusuna dönüştürür)      │
 └─────────────────────────┬───────────────────────────────┘
                           │
                           ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 2. Hibrit Arama & Skorlama Katmanı (Retriever)          │
 │    ├── Vektör Benzerliği (Dense):                      │
 │    │   qwen3-embedding-0.6b + NumPy Cosine Similarity   │
 │    │   Ağırlık: %65                                     │
 │    └── Sözcük & Başlık Eşleşmesi (Lexical):             │
 │        Başlık hiyerarşisi ve anahtar sözcük örtüşmesi  │
 │        Ağırlık: %35                                     │
 └─────────────────────────┬───────────────────────────────┘
                           │
                           ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 3. Skor Filtreleme & Eşik Kontrolü                      │
 │    • SCORE_THRESHOLD (0.32): Alakasız parçaları eler    │
 │    • TOP_K_CHUNKS (Varsayılan: 2): Optimum token bütçesi│
 │    • Negatif / Boş Eşleşme Guard:                      │
 │      Alakalı belge yoksa LLM çağrılmadan ret dönülür    │
 └─────────────────────────┬───────────────────────────────┘
                           │
                           ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 4. Grounded Generator (Microsoft Foundry Local)         │
 │    • Model: Phi-3.5-mini / Qwen3                        │
 │    • Sıfır Halüsinasyon Prensibi:                      │
 │      Yalnızca verilen kaynak metinlerden cevap üretir  │
 │    • Streaming & Erken Durdurma: Tekrarları engeller    │
 └─────────────────────────┬───────────────────────────────┘
                           │
                           ▼
 Yapılandırılmış Yanıt + Kaynak Belge Etiketleri + Metrikler (Gecikme, Parça Sayısı)
```

---

## 2. Katmanlar ve Bileşen Sorumlulukları

### 2.1. Ingestion & Chunking Katmanı (`ingest.py`)
- **Format Desteği:** `.txt`, `.md`, `.pdf` (pypdf ve chardet ile çoklu encoding desteği).
- **Contextual Chunking:** Belgeler parçalanırken kaynak dosya adı ve markdown başlık hiyerarşisi her parçanın başına üst veri olarak iliştirilir:
  ```text
  [Belge: dosya_adi.md | Konu: Başlık > Alt Başlık]
  İçerik...
  ```
- **Cümle Sınırı Koruması:** `CHUNK_MAX_CHARS` (1000) aşıldığında metin rastgele karakterlerden değil; nokta, soru işareti ve kelime sınırlarından bölünür. `CHUNK_OVERLAP_CHARS` (120) ile bağlam kopması engellenir.
- **Idempotent Kayıt:** Güncellenen belgelerin eski kayıtları SQLite'tan temizlenip yeni batch olarak eklenir (`clear_source`).

### 2.2. Veritabanı & İndeksleme Katmanı (`db/`)
- **SQLite Deposu:** `data/rag_store.db`.
- **Şema:**
  ```sql
  CREATE TABLE documents (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_name TEXT NOT NULL,
      chunk_index INTEGER NOT NULL,
      content TEXT NOT NULL,
      embedding TEXT NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(source_name, chunk_index)
  );
  ```
- **Vektör Saklama:** Vektörler JSON formatında serialize edilerek SQLite üzerinde tutulur ve bellek içi NumPy matris işlemleriyle milisaniye düzeyinde cosine similarity hesaplanır.

### 2.3. Hibrit Retrieval Katmanı (`rag/retriever.py`)
- **Dense Vector Search:** Sorgunun embedding vektörü ile veri tabanındaki tüm chunk vektörleri arasında Cosine Similarity hesaplanır.
- **Lexical/Title Boosting:** Dosya adı ve başlık hiyerarşisindeki kelime eşleşmeleri hesaplanarak anlamsal gürültü elenir.
- **Birleşik Skor:** `Hybrid = 0.65 * Dense + 0.35 * Lexical`.
- **Eşik Filtresi:** Skoru `SCORE_THRESHOLD` (0.32) altında kalan adaylar elenir. Boş bağlam durumunda LLM çağrısı yapılmadan anında ret yanıtı döner.

### 2.4. Üretim & Orkestrasyon Katmanı (`rag/generator.py`, `rag/pipeline.py`)
- **Foundry Local Entegrasyonu:** `foundry-local-sdk` üzerinden yerel model runtime'ına bağlanır.
- **Grounded System Prompt:** Modele harici dünya bilgisini kullanmaması, yalnızca verilen `<belge>` etiketli bağlamdan doğrudan alıntı ve mantıksal sentez yapması emredilir.
- **Anti-Loop & Temizleme:** Yanıt sırasında döngüye giren ifadeleri (`multi-gram loop detector`) erken keser; prompt sızıntılarını ve gereksiz etiketleri temizler.

---

## 3. Test ve Doğrulama

Birim ve entegrasyon testlerini çalıştırmak için:
```bash
python -m pytest tests/ -v
```

- `tests/test_chunker.py`: Paragraf ve cümle bölme, overlap, min/max karakter sınırları testleri.
- `tests/test_db_manager.py`: SQLite şeması, batch kayıt, cosine similarity ve kaynak temizleme testleri.
- `tests/test_ingest.py`: Dosya filtreleme, encoding tespiti ve çoklu format okuma testleri.
- `tests/test_pipeline.py`: Uçtan uca orkestrasyon, boş bağlam ret davranışı ve kaynak deduplication testleri.
- `tests/test_retriever.py`: Hibrit skorlama, dense/lexical ağırlıklandırma ve eşik testleri.
