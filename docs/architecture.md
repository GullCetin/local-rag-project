# Local RAG AI Assistant — Mimari Dokümantasyonu

Bu doküman, Microsoft Foundry Local tabanlı yerel RAG (Retrieval-Augmented Generation) sisteminin katmanlı mimarisini, veri akışını ve grounding prensiplerini açıklamaktadır.

---

## 1. Genel Mimari Şeması

```
Kullanıcı Sorusu (UI / CLI)
         ↓
 [1. Query Rewriter] ← (Sohbet Geçmişi ile Takip Sorusu Çözümleme)
         ↓
 Bağımsız Arama Sorgusu
         ↓
 [2. Hibrit Retriever]
    ├── Dense Vector Similarity (qwen3-embedding-0.6b, Cosine Sim) [Ağırlık: %60]
    └── Lexical / Title Match (Başlık, Dosya Adı, Terim Eşleşmesi) [Ağırlık: %40]
         ↓
 Top-4 İlgili Belge Alıntısı (Temiz XML `<belge>` Yapısı)
         ↓
 [3. Grounded Generator (Phi-3.5-mini)]
    ├── Level 1: Doğrudan Desteklenen Gerçekler (Direct Evidence)
    ├── Level 2: Mantıksal Çıkarımlar (Inference != Invention)
    └── Level 3: Desteklenmeyen Bilgiler (Zero Hallucination)
         ↓
 Yapılandırılmış Yanıt + Kaynak Belge Etiketleri
```

---

## 2. Katmanlar ve Sorumluluklar

### 2.1. Ingestion Katmanı (`ingest.py`)
- **Format Desteği:** `.txt`, `.md`, `.pdf` (pypdf ile).
- **Contextual Chunking:** Belgeler parçalanırken ait oldukları dosya adı ve markdown başlıkları (`[Belge: ... | Konu: ...]`) her parçanın başına eklenir.
- **Cümle Sınırı Koruması:** Paragraf çok uzunsa rastgele karakterlerden değil, cümle (`.?!`) ve kelime sınırlarından bölünür.
- **Idempotent Kayıt:** Güncellenen belgelerin eski kayıtları temizlenerek yeni batch eklenir (`clear_source`).

### 2.2. Veritabanı Katmanı (`db/`)
- **SQLite Veritabanı:** `data/rag_store.db`.
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

### 2.3. Hibrit Retrieval Katmanı (`rag/retriever.py`)
- **Dense Vector Search:** Sorgunun embedding vektörü ile veritabanındaki tüm vektörler arasında NumPy tabanlı Cosine Similarity hesaplanır.
- **Lexical/BM25 Boosting:** Dosya adı ve başlık terim eşleşmeleri hesaplanarak saf semantik gürültü elenir.
- **Birleşik Puanlama:** `Hybrid_Score = 0.60 * Dense_Score + 0.40 * Lexical_Score`.

### 2.4. Üretim Katmanı (`rag/generator.py`, `rag/pipeline.py`)
- **Query Reformulation:** Kullanıcı *"biraz daha detaylandırır mısın?"* gibi takip soruları sorduğunda önceki konuşma turlarını analiz ederek bağımsız arama sorgusuna dönüştürür.
- **Grounded Synthesis:** 60 maddelik Grounded Answer Generation prensiplerine göre yapılandırılmış sistem istemiyle yalnızca sağlanan alıntılardan yanıt üretir.

---

## 3. Test ve Doğrulama

Birim testleri çalıştırmak için:
```bash
python -m pytest tests/ -v
```
- `test_chunker.py`: 7 test (paragraf ve cümle bölme mantığı).
- `test_retriever.py`: 7 test (vektör benzerliği ve hibrit sözcük puanlaması).
