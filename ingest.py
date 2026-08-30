"""
ingest.py — Belge Yükleme (Ingestion) Scripti
===============================================
Bu script, docs/knowledge_base/ klasöründeki belgeleri okur,
paragraf bazlı chunk'lara böler, her chunk'ı embed eder
ve SQLite veritabanına kaydeder.

Güvenli yeniden çalıştırma: Aynı belge tekrar ingest edilirse
mevcut kayıtlar güncellenir (UPSERT), tekrar oluşturulmaz.

Kullanım:
  python ingest.py                         # knowledge_base/ klasörünü tara
  python ingest.py docs/sample_docs/       # Belirli bir klasörü kullan
  python ingest.py docs/sample_docs/x.txt  # Tek dosya ingest et

Desteklenen formatlar: .txt, .md, .pdf

Önemli Düzeltmeler:
  - Otomatik encoding tespiti (chardet): UTF-8, Windows-1254, ISO-8859-9 vb.
  - Gürültü satırı temizleme: resim dosyası adı, alt-text slug gibi anlamsız satırlar.
"""

import argparse
import logging
import os
import re
import sys

# Windows konsol Unicode uyumluluğu
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Proje kök dizinini Python path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    CHUNK_MAX_CHARS,
    CHUNK_MIN_CHARS,
    CHUNK_OVERLAP_CHARS,
    IGNORED_FILE_PATTERNS,
    KNOWLEDGE_BASE_DIR,
    MAX_CHUNKS_PER_FILE,
    MAX_INGEST_FILE_SIZE_MB,
    SUPPORTED_EXTENSIONS,
)
from db.manager import initialize_db, save_chunks_batch, get_chunk_count, clear_source
from rag.embedder import Embedder

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Encoding tespiti için TÜM olası Türkçe/Windows encoding'leri
_ENCODING_CANDIDATES = ["utf-8", "utf-8-sig", "windows-1254", "iso-8859-9", "cp857", "latin-1"]

# Gürültü satırı kalıpları: resim dosyası adları, URL slug'ları vb.
_NOISE_LINE_RE = re.compile(
    r"^[A-Za-z0-9\u00C0-\u024F][A-Za-z0-9\u00C0-\u024F._-]{2,60}$"
)

# Sayfa numarası kalıpları (örn: "Sayfa 1/10", "Page 3", "- 4 -")
_PAGE_NUMBER_RE = re.compile(
    r"^(?:sayfa\s*\d+(?:\s*/\s*\d+)?|page\s*\d+(?:\s*of\s*\d+)?|[-–—]\s*\d+\s*[-–—]|\d+\s*/\s*\d+)$",
    re.IGNORECASE,
)

# Kurumsal kalıp uyarılar (Boilerplate / Disclaimer)
_BOILERPLATE_PATTERNS = [
    re.compile(r"^.*(gizlidir|confidential|taslaktır|draft|tüm hakları saklıdır|all rights reserved).*$", re.IGNORECASE),
    re.compile(r"^.*(turna mobil uygulama|press enter or click to view image).*$", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Metin Okuyucular
# ---------------------------------------------------------------------------

def _detect_encoding(raw_bytes: bytes) -> str:
    """
    Ham byte dizisinden Türkçe karakter bütünlüğünü koruyan en doğru encoding'i seçer.

    Strateji (rules.txt: Adım 2 - Doküman Temizleme & Karakter Bütünlüğü):
      1. Aday encoding'leri decode et.
      2. İçinde '' (\\ufffd) veya bozuk byte kalıntısı olanları derhal ele.
      3. Türkçe karakter (ş, ğ, ü, ö, ç, ı, İ, Ğ, Ü, Ş, Ö, Ç) frekansı en yüksek olanı seç.
    """
    turkish_chars = set("şğüöçıİĞÜŞÖÇ")
    candidates = ["utf-8", "iso-8859-9", "windows-1254", "cp857", "latin-1"]

    best_enc = "utf-8"
    best_score = -1

    for enc in candidates:
        try:
            # errors='strict' ile dene, bozuk byte varsa yakala
            decoded = raw_bytes.decode(enc, errors="replace")
            # Eğer replacement char () varsa bu encoding hatalıdır, puanı kır
            bad_char_count = decoded.count("\ufffd") + decoded.count("")
            if bad_char_count > 0:
                score = -bad_char_count
            else:
                # Türkçe karakter sayısına göre pozitif puan ver
                tr_count = sum(1 for ch in decoded if ch in turkish_chars)
                score = 1000 + tr_count

            if score > best_score:
                best_score = score
                best_enc = enc
        except Exception:
            continue

    logger.info(f"  Encoding analiz sonucu: '{best_enc}' (Skor: {best_score})")
    return best_enc


def read_txt(path: str) -> str:
    """
    TXT ve Markdown dosyalarını okur.

    UTF-8, Windows-1254, ISO-8859-9 gibi farklı encoding'leri otomatik
    tespit eder. Türkçe karakterleri (ş, ğ, ü, ö, ı, ç) doğru okur.
    """
    with open(path, "rb") as f:
        raw_bytes = f.read()

    encoding = _detect_encoding(raw_bytes)
    try:
        text = raw_bytes.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        # Tamamen beklenmedik bir hata: latin-1 her zaman çalışır
        text = raw_bytes.decode("latin-1")
        logger.warning(f"Encoding hatası ({encoding}), latin-1 kullanıldı: {path}")

    logger.info(f"  Encoding: {encoding} → {os.path.basename(path)}")
    return text


def read_pdf(path: str) -> str:
    """PDF dosyasından düz metin çıkarır (pypdf kullanır)."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("pypdf kurulu değil. 'pip install pypdf' çalıştırın.")

    reader = PdfReader(path)
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)
    return "\n\n".join(pages_text)


def read_document(path: str) -> str:
    """
    Dosya uzantısına göre uygun okuyucuyu seçer ve metni döner.

    Args:
        path: Dosya yolu

    Returns:
        Belgenin ham metin içeriği

    Raises:
        ValueError: Desteklenmeyen dosya formatı
        FileNotFoundError: Dosya bulunamadı
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dosya bulunamadı: {path}")

    ext = os.path.splitext(path)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Desteklenmeyen format '{ext}'. "
            f"Desteklenenler: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    if ext == ".pdf":
        return read_pdf(path)
    else:
        # .txt ve .md için aynı okuyucu
        return read_txt(path)


# ---------------------------------------------------------------------------
# Doküman Temizleme & Ön İşleme (rules.txt: Adım 2 - Doküman Temizleme)
# ---------------------------------------------------------------------------

def _is_noise_line(line: str) -> bool:
    """
    Satırın gürültü, sayfa numarası, alt-text veya kalıp uyarı içerip içermediğini denetler.
    """
    stripped = line.strip()
    if not stripped:
        return False

    # Sayfa numarası kontrolü
    if _PAGE_NUMBER_RE.match(stripped):
        return True

    # Kalıp uyarı / disclaimer kontrolü
    for bp in _BOILERPLATE_PATTERNS:
        if bp.match(stripped):
            return True

    # Boşluksuz slug / resim adı kontrolü
    if _NOISE_LINE_RE.match(stripped) and len(stripped) < 50:
        return True

    if "-" in stripped and " " not in stripped and len(stripped) < 60:
        return True

    return False


def clean_document_text(text: str) -> str:
    """
    rules.txt Adım 2 İlkelerine Göre Doküman Temizliği:
      - Header / Footer tekrarlarını tespit edip eler.
      - Sayfa numaraları ve baskı artıklarını temizler.
      - Resim isimleri ve navigasyon slug'larını ayıklar.
      - Ardışık boş satırları normalize eder.
    """
    if not text:
        return ""

    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        if _is_noise_line(line):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def chunk_text(text: str, source_name: str = "") -> list[str]:
    """
    rules.txt Adım 5 İlkelerine Göre Yapısal & Bağlamsal Chunking:
      1. Ham metni temizle (clean_document_text).
      2. Paragraf ve bölüm sınırlarına göre ayır.
      3. Markdown (#, ##) ve numaralı ("1.", "2.") başlıkları hiyerarşik takip et.
      4. Chunk'ların başına [Belge: ... | Konu: ...] bağlamını zerk et (Contextual Injection).
      5. Uzun parçaları cümle bütünlüğünü ve overlap'i koruyarak böl.

    Args:
        text: Ham metin
        source_name: Kaynak belge adı

    Returns:
        Zenginleştirilmiş chunk listesi
    """
    if not text or not text.strip():
        return []

    cleaned_text = clean_document_text(text)
    if not cleaned_text:
        return []

    raw_paragraphs = cleaned_text.split("\n\n")
    chunks = []
    current_section = ""

    # Numaralı bölüm başlığı regex'i (ör: "5. Pilotlar havada uyur mu?")
    _numbered_section_re = re.compile(r"^\d{1,2}\.\s+(.{4,90})$")

    # 1. Aşama: Başlıkları ve paragrafları düzenle
    structured_items = []
    for para in raw_paragraphs:
        para = para.strip()
        if not para:
            continue

        # Başlık satırı tespiti (# veya ##)
        if para.startswith("#"):
            lines = para.split("\n")
            header_line = lines[0].lstrip("#").strip()
            current_section = header_line
            if len(lines) > 1:
                body = "\n".join(lines[1:]).strip()
                if body:
                    structured_items.append((current_section, body))
            continue

        first_line = para.split("\n")[0].strip()
        m = _numbered_section_re.match(first_line)
        if m:
            current_section = m.group(1).strip()

        structured_items.append((current_section, para))

    # 2. Aşama: Akıllı Paragraf Birleştirme (Smart Paragraph Merging)
    # Giriş cümleleri (ör: ":" ile bitenler veya bir sonraki liste maddesine giriş yapanlar) birleştirilir
    merged_items = []
    idx = 0
    while idx < len(structured_items):
        sec, content = structured_items[idx]
        
        if idx + 1 < len(structured_items):
            next_sec, next_content = structured_items[idx + 1]
            is_lead_in = content.endswith(":") or (
                len(content) < 200 and next_content.lstrip().startswith(("- ", "* ", "1. ", "• "))
            )
            if sec == next_sec and is_lead_in:
                content = f"{content}\n{next_content}"
                idx += 1  # sonraki paragrafı tükettik
        
        merged_items.append((sec, content))
        idx += 1

    # 3. Aşama: Bağlam enjeksiyonu ve boyut kontrolü
    for sec, para in merged_items:
        if len(para) < CHUNK_MIN_CHARS:
            continue

        context_prefix = ""
        prefix_parts = []
        if source_name:
            prefix_parts.append(f"Belge: {source_name}")
        if sec:
            prefix_parts.append(f"Konu: {sec}")
        if prefix_parts:
            context_prefix = f"[{' | '.join(prefix_parts)}]\n"

        if len(para) > CHUNK_MAX_CHARS:
            sub_chunks = _split_long_paragraph(para)
            for sub in sub_chunks:
                chunks.append(f"{context_prefix}{sub}".strip())
        else:
            chunks.append(f"{context_prefix}{para}".strip())

    return chunks


def _split_long_paragraph(para: str) -> list[str]:
    """
    Uzun metinleri cümle sınırlarında ve CHUNK_OVERLAP_CHARS örtüşmesiyle böler.
    rules.txt Adım 5: Cümlelerin yarım kalmasını ve bağlam kopuşunu önler.
    """
    sentences = re.split(r"(?<=[.!?])\s+", para)
    result = []
    current_sentences = []
    current_len = 0

    for sentence in sentences:
        s = sentence.strip()
        if not s:
            continue

        # Tek bir cümle CHUNK_MAX_CHARS'tan uzunsa kelimelerden böl
        if len(s) > CHUNK_MAX_CHARS:
            if current_sentences:
                chunk_str = " ".join(current_sentences)
                if len(chunk_str) >= CHUNK_MIN_CHARS:
                    result.append(chunk_str)
                current_sentences = []
                current_len = 0

            words = s.split()
            w_chunk = []
            w_len = 0
            for w in words:
                if w_len + len(w) + 1 <= CHUNK_MAX_CHARS:
                    w_chunk.append(w)
                    w_len += len(w) + 1
                else:
                    if w_chunk:
                        result.append(" ".join(w_chunk))
                    w_chunk = [w]
                    w_len = len(w)
            if w_chunk and len(" ".join(w_chunk)) >= CHUNK_MIN_CHARS:
                result.append(" ".join(w_chunk))
            continue

        if current_len + len(s) + 1 <= CHUNK_MAX_CHARS:
            current_sentences.append(s)
            current_len += len(s) + 1
        else:
            if current_sentences:
                chunk_str = " ".join(current_sentences)
                if len(chunk_str) >= CHUNK_MIN_CHARS:
                    result.append(chunk_str)
                
                # Overlap: Son cümleyi bir sonraki parçaya bağla (bağlam sürekliliği)
                if len(current_sentences) > 1 and len(current_sentences[-1]) <= CHUNK_OVERLAP_CHARS:
                    current_sentences = [current_sentences[-1], s]
                    current_len = sum(len(x) + 1 for x in current_sentences)
                else:
                    current_sentences = [s]
                    current_len = len(s)
            else:
                current_sentences = [s]
                current_len = len(s)

    if current_sentences:
        chunk_str = " ".join(current_sentences)
        if len(chunk_str) >= CHUNK_MIN_CHARS:
            result.append(chunk_str)

    return result


# ---------------------------------------------------------------------------
# Dosya Keşfi
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Dosya Keşfi & Filtreleme (rules.txt: Adım 1 - Bilgi Envanteri)
# ---------------------------------------------------------------------------

def _is_ignored_filename(filename: str) -> bool:
    """Hassas, çöp veya lisans dosyalarını regex listesine göre eler."""
    fn_lower = filename.lower()
    for pattern in IGNORED_FILE_PATTERNS:
        if re.match(pattern, fn_lower):
            return True
    return False


def discover_files(source: str) -> list[str]:
    """
    Verilen yoldaki desteklenen ve geçerli belgeleri keşfeder.
    Kara listedeki lisans ve teknik dosyalar otomatik filtrelenir.
    """
    if os.path.isfile(source):
        fname = os.path.basename(source)
        if _is_ignored_filename(fname):
            logger.warning(f"Dosya kara listede olduğundan atlandı: {fname}")
            return []
        ext = os.path.splitext(source)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            return [source]
        else:
            logger.warning(f"Atlandı (desteklenmeyen format): {source}")
            return []

    if os.path.isdir(source):
        files = []
        for fname in sorted(os.listdir(source)):
            if _is_ignored_filename(fname):
                logger.info(f"Filtrelendi (teknik/lisans/kara liste): {fname}")
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                files.append(os.path.join(source, fname))
        return files

    raise FileNotFoundError(f"Yol bulunamadı: {source}")


# ---------------------------------------------------------------------------
# Ana Ingestion Fonksiyonu
# ---------------------------------------------------------------------------

def ingest_file(path: str, embedder: Embedder) -> int:
    """
    Tek bir dosyayı chunk'lara böler, embed eder ve DB'ye kaydeder.

    Önceden boyut ve chunk sayısı limiti kontrolü yapılır:
      - MAX_INGEST_FILE_SIZE_MB'den büyük dosyalar atlanır
      - MAX_CHUNKS_PER_FILE'dan fazla chunk varsa ilk N tanesi alınır

    Args:
        path     : Dosya yolu
        embedder : Yüklenmiş Embedder instance'ı

    Returns:
        Kaydedilen chunk sayısı
    """
    source_name = os.path.basename(path)
    logger.info(f"İşleniyor: {source_name}")

    # 0. Dosya boyutu güvenlik kontrolü
    file_size_mb = os.path.getsize(path) / (1024 * 1024)
    if file_size_mb > MAX_INGEST_FILE_SIZE_MB:
        logger.warning(
            f"  Dosya çok büyük ({file_size_mb:.1f}MB > {MAX_INGEST_FILE_SIZE_MB}MB), atlanıyor: {source_name}\n"
            f"  İpuçu: config.py'de MAX_INGEST_FILE_SIZE_MB değerini artırabilirsiniz."
        )
        return 0

    # 1. Metni oku
    try:
        text = read_document(path)
    except Exception as e:
        logger.error(f"Okunamadı ({source_name}): {e}")
        return 0

    if not text.strip():
        logger.warning(f"Boş belge, atlanıyor: {source_name}")
        return 0

    # 2. Chunk'lara böl (başlık ve belge bağlamıyla)
    chunks = chunk_text(text, source_name=source_name)
    if not chunks:
        logger.warning(f"Chunk üretilemedi: {source_name}")
        return 0

    # Chunk sayısı limiti kontrolü
    original_count = len(chunks)
    if original_count > MAX_CHUNKS_PER_FILE:
        chunks = chunks[:MAX_CHUNKS_PER_FILE]
        logger.warning(
            f"  {original_count} chunk üretildi, limit aşıldı → ilk {MAX_CHUNKS_PER_FILE} chunk kullanılıyor: {source_name}"
        )
    else:
        logger.info(f"  {len(chunks)} chunk üretildi")

    # 3. Her chunk'ı embed et + batch kaydet
    batch = []
    for idx, chunk in enumerate(chunks):
        try:
            vector = embedder.embed(chunk)
            batch.append((source_name, idx, chunk, vector))
        except Exception as e:
            logger.error(f"  Chunk {idx} embed hatası: {e}")
            continue

    if not batch:
        logger.error(f"Hiçbir chunk embed edilemedi: {source_name}")
        return 0

    # Belgenin eski kayıtlarını temizle ve güncel batch'i kaydet (Tam Idempotency)
    clear_source(source_name)
    save_chunks_batch(batch)
    logger.info(f"  ✓ {len(batch)} chunk kaydedildi → '{source_name}'")
    return len(batch)


def run_ingestion(source_path: str) -> None:
    """
    Ingestion akışını başlatır.

    1. DB'yi başlat
    2. Embedding modelini yükle
    3. Dosyaları keşfet
    4. Her dosyayı ingest et
    5. Özet rapor göster

    Args:
        source_path: İşlenecek dosya veya klasör yolu
    """
    print("\n" + "=" * 55)
    print("  Local RAG — Belge Yükleme (Ingestion)")
    print("=" * 55)

    # DB başlat
    initialize_db()

    # Dosyaları keşfet
    try:
        files = discover_files(source_path)
    except FileNotFoundError as e:
        print(f"\n[HATA] {e}")
        sys.exit(1)

    if not files:
        print(f"\n[UYARI] İşlenecek belge bulunamadı: {source_path}")
        print(f"Desteklenen formatlar: {', '.join(SUPPORTED_EXTENSIONS)}")
        sys.exit(0)

    print(f"\nBulunan belge sayısı : {len(files)}")
    for f in files:
        print(f"  • {os.path.basename(f)}")

    # Embedding modelini yükle
    print(f"\nEmbedding modeli yükleniyor...")
    embedder = Embedder()
    try:
        embedder.load()
    except Exception as e:
        print(f"\n[HATA] Embedding modeli yüklenemedi: {e}")
        sys.exit(1)

    # Her dosyayı işle
    print(f"\nBelgeler işleniyor...\n")
    total_chunks = 0
    success_count = 0

    for file_path in files:
        n = ingest_file(file_path, embedder)
        total_chunks += n
        if n > 0:
            success_count += 1

    # Özet rapor
    print("\n" + "-" * 55)
    print(f"  Tamamlandı!")
    print(f"  İşlenen dosya : {success_count}/{len(files)}")
    print(f"  Toplam chunk  : {total_chunks}")
    print(f"  DB'deki chunk : {get_chunk_count()}")
    print("-" * 55 + "\n")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Local RAG — Belge ingestion scripti",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python ingest.py                           # knowledge_base/ klasörünü tara
  python ingest.py docs/sample_docs/         # Belirli bir klasörü kullan
  python ingest.py docs/sample_docs/x.txt   # Tek dosya
        """,
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=KNOWLEDGE_BASE_DIR,
        help=f"İşlenecek dosya veya klasör (varsayılan: {KNOWLEDGE_BASE_DIR})",
    )
    args = parser.parse_args()

    run_ingestion(args.source)
