"""
ui/app.py — Local RAG Asistanı (Profesyonel Light UI/UX)
=========================================================
Görsel referansa birebir uygun, Türkçe/İngilizce dil desteği,
sabit sidebar alt menü, kaydırmalı doküman listesi, anlık önizleme,
örnek başlangıç soruları ve optimize edilmiş tipografi.

Çalıştır:
  streamlit run ui/app.py
"""

import os
import sys
import time
import logging
import html
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import importlib
import config
importlib.reload(config)

from config import AVAILABLE_LLM_MODELS, KNOWLEDGE_BASE_DIR, SUPPORTED_EXTENSIONS

# ---------------------------------------------------------------------------
# Sayfa Yapılandırması
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Local RAG Asistanı",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Dil Sözlüğü
# ---------------------------------------------------------------------------
LANG = {
    "tr": {
        "app_title":        "Local RAG Asistanı",
        "sys_status":       "SİSTEM DURUMU",
        "models_ready":     "Modeller Hazır (Yerel)",
        "model_label":      "Model",
        "doc_upload":       "DOKÜMAN YÜKLE",
        "upload_btn":       "Dosyaları Seçin veya Sürükleyin",
        "upload_hint":      ".txt, .md veya .pdf dosyaları desteklenir",
        "indexed_docs":     "İNDEKSLENEN DOKÜMANLAR",
        "no_docs":          "Henüz doküman yüklenmedi.",
        "total_docs":       "{n} doküman · {c} parça",
        "clear_chat":       "🗑️ Sohbeti Temizle",
        "privacy":          "🔒 Verileriniz cihazınızdan asla çıkmaz",
        "placeholder":      "Dokümanlarınız hakkında soru sorun...",
        "searching":        "Yanıt aranıyor...",
        "loading":          "Modeller yükleniyor...",
        "err_loading":      "Model yükleme hatası",
        "err_check":        "Foundry Local'in çalıştığını kontrol edin.",
        "err_no_docs":      "İndekslenmiş doküman yok. Lütfen soldaki panelden doküman yükleyin.",
        "err_generic":      "Beklenmedik hata",
        "src_label":        "Kaynak:",
        "preview_title":    "Doküman Önizlemesi",
        "preview_close":    "Kapat",
        "upload_ok":        "✓ {f} ({n} parça eklendi)",
        "upload_err":       "✕ {f}: {e}",
        "lang_label":       "Dil",
        "del_btn":          "✕",
        "prv_btn":          "👁",
        "welcome_title":    "Doküman Asistanınıza Hoş Geldiniz",
        "welcome_subtitle": "Yüklediğiniz dokümanlar hakkında detaylı sorular sorabilir veya aşağıdaki örnek sorulardan birini seçebilirsiniz:",
        "starter_q1":       "Arabica ve Robusta kahve çekirdekleri arasındaki temel farklar nelerdir?",
        "starter_q2":       "Zero Trust mimarisinin temel prensipleri nelerdir?",
        "starter_q3":       "Foundry Local SDK nedir ve yerel model nasıl bağlanır?",
        "starter_q4":       "RAG mimarisinde Chunking ve Hibrit Arama neden önemlidir?",
    },
    "en": {
        "app_title":        "Local RAG Assistant",
        "sys_status":       "SYSTEM STATUS",
        "models_ready":     "Models Ready (Local)",
        "model_label":      "Model",
        "doc_upload":       "DOCUMENT UPLOAD",
        "upload_btn":       "Browse Files or Drag & Drop",
        "upload_hint":      ".txt, .md or .pdf files supported",
        "indexed_docs":     "INDEXED DOCUMENTS",
        "no_docs":          "No documents indexed yet.",
        "total_docs":       "{n} docs · {c} chunks",
        "clear_chat":       "🗑️ Clear Chat",
        "privacy":          "🔒 Your data never leaves this device",
        "placeholder":      "Ask about your documents...",
        "searching":        "Searching...",
        "loading":          "Loading models...",
        "err_loading":      "Model loading error",
        "err_check":        "Check that Foundry Local is running.",
        "err_no_docs":      "No indexed documents. Please upload from the left panel.",
        "err_generic":      "Unexpected error",
        "src_label":        "Source:",
        "preview_title":    "Document Preview",
        "preview_close":    "Close",
        "upload_ok":        "✓ {f} ({n} chunks added)",
        "upload_err":       "✕ {f}: {e}",
        "lang_label":       "Language",
        "del_btn":          "✕",
        "prv_btn":          "👁",
        "welcome_title":    "Welcome to your Document Assistant",
        "welcome_subtitle": "Ask detailed questions about your indexed documents or try one of the starter questions below:",
        "starter_q1":       "What are the key differences between Arabica and Robusta coffee beans?",
        "starter_q2":       "What are the core principles of Zero Trust architecture?",
        "starter_q3":       "What is Foundry Local SDK and how do you connect local models?",
        "starter_q4":       "Why are Chunking and Hybrid Search critical in RAG architecture?",
    },
}

def t(key: str, **kwargs) -> str:
    lang = st.session_state.get("lang", "tr")
    text = LANG.get(lang, LANG["tr"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


# ---------------------------------------------------------------------------
# Tüm CSS & Tipografi
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

/* Tipografi - Material Symbol ikonlarını Inter ile ezmeden korur */
html, body, [class*="css"], .stApp, p, label, input, textarea, button,
div:not([class*="material-symbols"]):not([data-testid*="Icon"]),
span:not([class*="material-symbols"]):not([data-testid*="Icon"]):not([class*="stIcon"]) {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}

/* Material Icons simgelerini netleştir */
.material-symbols-rounded, [data-testid="stIconMaterial"], [class*="material-symbols"] {
    font-family: 'Material Symbols Rounded' !important;
    font-style: normal !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    display: inline-block !important;
    white-space: nowrap !important;
    word-wrap: normal !important;
    direction: ltr !important;
    -webkit-font-feature-settings: 'liga' !important;
    -webkit-font-smoothing: antialiased !important;
}

html, body, .stApp {
    background-color: #F0F4F8 !important;
    color: #1E293B !important;
    font-size: 16.5px !important;
    line-height: 1.65 !important;
}

header[data-testid="stHeader"] {
    background-color: #F8F5EE !important;
    border-bottom: 1px solid #E8E0D0 !important;
}
#MainMenu, footer, [data-testid="stDecoration"] { display: none !important; }

/* ── Sidebar ────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #EBF1F6 !important;
    border-right: 1px solid #D1DCE8 !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 0.9rem 0.9rem !important;
    display: flex !important;
    flex-direction: column !important;
    height: 100vh !important;
    overflow-y: auto !important;
    gap: 0.45rem !important;
}

/* Başlık (Sidebar collapse hizalı) */
.panel-brand {
    font-size: 1.22rem;
    font-weight: 700;
    color: #1E293B;
    padding: 0.25rem 0 0.65rem 0;
    border-bottom: 1.5px solid #D1DCE8;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.5rem;
    flex-shrink: 0;
    letter-spacing: -0.01em;
}

/* Kart */
.s-card {
    background: #FFFFFF;
    border: 1px solid #D8E2EC;
    border-radius: 10px;
    padding: 0.75rem 0.9rem;
    margin-bottom: 0.45rem;
    flex-shrink: 0;
}
.s-label {
    font-size: 0.82rem;
    font-weight: 700;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
}

/* Sistem durumu */
.status-ok {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.96rem;
    font-weight: 600;
    color: #16A34A;
}
.dot-green { width: 10px; height: 10px; background: #22C55E; border-radius: 50%; }

/* Dosya yükleyici alanı */
[data-testid="stFileUploader"] {
    background-color: #F8FAFC !important;
    border: 1.5px dashed #93C5FD !important;
    border-radius: 10px !important;
    padding: 0.3rem !important;
}
[data-testid="stFileUploader"] section {
    background-color: transparent !important;
    border: none !important;
    padding: 0.4rem !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] {
    display: none !important;
}
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] p { color: #334155 !important; font-size: 0.90rem !important; }
[data-testid="stFileUploader"] button {
    background: #FFFFFF !important;
    color: #1E293B !important;
    border: 1.5px solid #CBD5E1 !important;
    border-radius: 7px !important;
    font-size: 0.90rem !important;
    font-weight: 600 !important;
    padding: 0.4rem 0.85rem !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploader"] button:hover {
    background: #EFF6FF !important;
    border-color: #3B82F6 !important;
    color: #1D4ED8 !important;
}

/* İndekslenen dokümanlar listesi */
.doc-item-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.4rem 0.2rem;
    border-bottom: 1px solid #EEF2F6;
    gap: 0.4rem;
}
.doc-item-row:last-child { border-bottom: none; }
.doc-item-name {
    font-size: 0.95rem;
    color: #1E293B;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
}
.doc-count-footer {
    font-size: 0.88rem;
    color: #475569;
    font-weight: 600;
    margin-top: 0.45rem;
    padding-top: 0.4rem;
    border-top: 1px solid #E2E8F0;
}

/* Sidebar butonları genel */
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    font-size: 0.92rem !important;
}

/* Sohbeti Temizle Butonu */
div[data-testid="stSidebar"] div.clear-chat-container button {
    background: #FFFFFF !important;
    color: #DC2626 !important;
    border: 1.5px solid #FCA5A5 !important;
    border-radius: 9px !important;
    padding: 0.65rem 1rem !important;
    font-size: 0.98rem !important;
    font-weight: 600 !important;
    transition: all 0.2s ease-in-out !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
}
div[data-testid="stSidebar"] div.clear-chat-container button:hover {
    background: #FEE2E2 !important;
    border-color: #EF4444 !important;
    color: #B91C1C !important;
}

/* Alt alan */
.sidebar-bottom {
    padding-top: 0.6rem;
    border-top: 1px solid #D1DCE8;
    margin-top: 0.6rem;
}
.privacy-note {
    font-size: 0.84rem;
    color: #64748B;
    text-align: center;
    margin-top: 0.5rem;
    font-weight: 500;
}

/* Flash mesajı efekti */
[data-testid="stSidebar"] [data-testid="stAlert"] {
    animation: flashFadeOut 0.5s ease 2s forwards;
}
@keyframes flashFadeOut {
    0% { opacity: 1; }
    99% { opacity: 0; max-height: 0; margin: 0; padding: 0; }
    100% { opacity: 0; display: none; max-height: 0; margin: 0; padding: 0; }
}

/* Dil radio */
[data-testid="stRadio"] > div { flex-direction: row !important; gap: 0.75rem !important; }
[data-testid="stRadio"] label { font-size: 0.88rem !important; font-weight: 500 !important; }

/* ── Karşılama & Başlangıç Soru Kartları ─────────── */
.welcome-container {
    max-width: 820px;
    margin: 2.2rem auto 1.5rem auto;
    text-align: center;
}
.welcome-title {
    font-size: 1.65rem;
    font-weight: 700;
    color: #0F172A;
    margin-bottom: 0.5rem;
    letter-spacing: -0.02em;
}
.welcome-subtitle {
    font-size: 1.02rem;
    color: #64748B;
    margin-bottom: 1.5rem;
    line-height: 1.55;
}
.starter-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.85rem;
    margin-top: 1.0rem;
    text-align: left;
}

/* Başlangıç Soru Butonları */
div[data-testid="stVerticalBlock"] div.starter-card-wrapper button {
    background: #FFFFFF !important;
    border: 1.5px solid #CBD5E1 !important;
    border-radius: 12px !important;
    padding: 0.95rem 1.15rem !important;
    font-size: 0.98rem !important;
    font-weight: 500 !important;
    color: #1E293B !important;
    text-align: left !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
    transition: all 0.2s ease !important;
    height: 100% !important;
    min-height: 85px !important;
    display: flex !important;
    align-items: center !important;
    line-height: 1.45 !important;
}
div[data-testid="stVerticalBlock"] div.starter-card-wrapper button:hover {
    border-color: #2563EB !important;
    background: #F8FAFC !important;
    color: #1D4ED8 !important;
    box-shadow: 0 4px 12px rgba(37,99,235,0.12) !important;
    transform: translateY(-2px);
}

/* ── Chat Mesajları ──────────────────────────────── */
/* Kullanıcı → SAĞ */
.msg-user {
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
    gap: 0.75rem;
    margin: 1.25rem 0;
}
.msg-user .bubble {
    background: #0E2538;
    color: #FFFFFF;
    padding: 1.05rem 1.35rem;
    border-radius: 18px 18px 4px 18px;
    font-size: 1.08rem;
    line-height: 1.7;
    max-width: 76%;
    box-shadow: 0 2px 8px rgba(14,37,56,0.15);
    word-break: break-word;
}
.user-av {
    width: 38px; height: 38px;
    border-radius: 50%;
    background: #1E3A5F;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.15rem; flex-shrink: 0;
}

/* Asistan → SOL */
.msg-bot {
    display: flex;
    justify-content: flex-start;
    align-items: flex-start;
    gap: 0.75rem;
    margin: 1.25rem 0;
}
.msg-bot .bubble {
    background: #FFFFFF;
    border: 1.5px solid #CBD5E1;
    color: #0F172A;
    padding: 1.1rem 1.4rem;
    border-radius: 18px 18px 18px 4px;
    font-size: 1.08rem;
    line-height: 1.72;
    max-width: 78%;
    box-shadow: 0 3px 10px rgba(0,0,0,0.05);
    word-break: break-word;
}
.bot-meta {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
    flex-shrink: 0;
}
.bot-av {
    width: 38px; height: 38px;
    border-radius: 10px;
    background: #E0F2FE;
    border: 1px solid #BAE6FD;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem;
}
.latency-tag {
    font-size: 0.78rem;
    color: #64748B;
    font-weight: 600;
}

/* Kaynak satırı */
.src-row {
    margin-top: 0.85rem;
    padding-top: 0.65rem;
    border-top: 1px solid #E2E8F0;
    font-size: 0.90rem;
    color: #475569;
}
.src-chips { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 0.35rem; }
.src-chip {
    background: rgba(37,99,235,0.08);
    border: 1px solid rgba(37,99,235,0.25);
    color: #1D4ED8;
    padding: 0.25rem 0.6rem;
    border-radius: 6px;
    font-size: 0.86rem;
    font-weight: 600;
}

/* Chat input */
[data-testid="stChatInput"] {
    background: #FFFFFF !important;
    border: 1.5px solid #94A3B8 !important;
    border-radius: 14px !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.07) !important;
    max-width: 880px !important;
    margin: 0 auto !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.2) !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: #0F172A !important;
    font-size: 1.05rem !important;
    line-height: 1.55 !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #94A3B8 !important; }
[data-testid="stChatInput"] button {
    background: #0E2538 !important;
    color: #FFF !important;
    border-radius: 50% !important;
    border: none !important;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session State
# ---------------------------------------------------------------------------
def _init() -> None:
    defaults = {
        "pipeline":           None,
        "pipeline_status":    "not_started",
        "messages":           [],
        "error_message":      None,
        "upload_flash":       [],
        "last_upload_key":    None,
        "uploader_key_idx":   0,
        "lang":               "tr",
        "preview_doc":        None,
        "pending_question":   None,
        "selected_model":     getattr(config, "LLM_MODEL_ALIAS", "phi-3.5-mini"),
        "switching_model":    False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ---------------------------------------------------------------------------
# Pipeline (Önbellekli)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _load_pipeline():
    from rag.pipeline import RAGPipeline
    p = RAGPipeline()
    p.load()
    return p


# ---------------------------------------------------------------------------
# Dosya İngestion
# ---------------------------------------------------------------------------
def _ingest(file_path: str, source_name: str) -> dict:
    try:
        from ingest import chunk_text, read_document
        from db.manager import initialize_db, save_chunks_batch, clear_source

        initialize_db()
        text = read_document(file_path)
        if not text.strip():
            return {"ok": False, "chunks": 0, "error": "Dosya boş veya okunamadı."}

        chunks = chunk_text(text, source_name=source_name)
        if not chunks:
            return {"ok": False, "chunks": 0, "error": "Parça oluşturulamadı."}

        pip = st.session_state.get("pipeline")
        if pip is not None:
            embedder = pip._embedder
        else:
            from rag.embedder import Embedder
            embedder = Embedder()
            embedder.load()

        batch = []
        for idx, chunk in enumerate(chunks):
            try:
                vector = embedder.embed(chunk)
                batch.append((source_name, idx, chunk, vector))
            except Exception as e:
                logging.warning(f"Chunk {idx} embed hatası: {e}")

        if not batch:
            return {"ok": False, "chunks": 0, "error": "Vektör üretilemedi."}

        clear_source(source_name)
        save_chunks_batch(batch)
        return {"ok": True, "chunks": len(batch), "error": None}
    except Exception as e:
        return {"ok": False, "chunks": 0, "error": str(e)}


# ---------------------------------------------------------------------------
# Doküman Önizleme
# ---------------------------------------------------------------------------
def _preview_text(source_name: str, max_chars: int = 3000) -> str:
    try:
        from db.manager import get_all_chunks
        chunks = get_all_chunks()
        parts = [c["content"] for c in chunks if c["source_name"] == source_name]
        full = "\n\n".join(parts)
        return (full[:max_chars] + "\n\n...(kısaltıldı)") if len(full) > max_chars else full
    except Exception as e:
        return f"Önizleme yüklenemedi: {e}"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def render_sidebar() -> None:
    with st.sidebar:
        # Marka başlığı (Emojisiz, modern & sidebar collapse hizalı)
        st.markdown(
            f'<div class="panel-brand"><span>{t("app_title")}</span></div>',
            unsafe_allow_html=True,
        )

        # Dil Seçimi
        lang_idx = 0 if st.session_state.lang == "tr" else 1
        choice = st.radio(
            t("lang_label"),
            ["🇹🇷 Türkçe", "🇬🇧 English"],
            index=lang_idx,
            horizontal=True,
            label_visibility="collapsed",
            key="lang_radio",
        )
        new_lang = "tr" if "🇹🇷" in choice else "en"
        if new_lang != st.session_state.lang:
            st.session_state.lang = new_lang
            st.rerun()

        # ── Model Seçici (Emojisiz) ──────────────────────
        models_list = getattr(config, "AVAILABLE_LLM_MODELS", [
            ("qwen3-1.7b",   "Qwen3-1.7B  ⚡ (Hızlı ~8-15sn, 1.4GB)"),
            ("qwen3-4b",     "Qwen3-4B   ⚡⚡ (Dengeli ~20-35sn, 2.8GB)"),
            ("phi-3.5-mini", "Phi-3.5-mini  (Yavaş ~30-60sn, 2.6GB)"),
        ])
        model_aliases  = [alias for alias, _ in models_list]
        model_labels   = [label for _, label in models_list]
        current_idx    = model_aliases.index(st.session_state.selected_model) \
                         if st.session_state.selected_model in model_aliases else 0
        
        label_txt = t("model_label")
        sel_label = st.selectbox(
            label_txt,
            options=model_labels,
            index=current_idx,
            key="model_selector",
        )
        chosen_alias = model_aliases[model_labels.index(sel_label)]
        if chosen_alias != st.session_state.selected_model:
            st.session_state.selected_model = chosen_alias
            pip = st.session_state.get("pipeline")
            if pip is not None:
                with st.spinner("Model değiştiriliyor..."):
                    try:
                        pip.switch_llm_model(chosen_alias)
                        st.success(f"✓ Model: {chosen_alias}")
                    except Exception as e:
                        st.error(f"Model değiştirme hatası: {e}")
            st.rerun()

        # Sistem Durumu
        st.markdown(f"""
        <div class="s-card">
            <div class="s-label">{t("sys_status")}</div>
            <div class="status-ok">
                <span class="dot-green"></span>
                <span>{t("models_ready")}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Doküman Yükleme Kartı
        st.markdown(f"""
        <div class="s-card" style="margin-bottom:0.15rem;">
            <div class="s-label">{t("doc_upload")}</div>
            <div style="font-size:0.86rem; color:#64748B; margin-bottom:0.4rem;">{t("upload_hint")}</div>
        </div>
        """, unsafe_allow_html=True)

        uploader_key = f"uploader_{st.session_state.uploader_key_idx}"
        uploaded = st.file_uploader(
            label=t("upload_btn"),
            type=["txt", "md", "pdf"],
            label_visibility="collapsed",
            key=uploader_key,
            help=t("upload_hint"),
        )

        if uploaded is not None:
            fkey = f"{uploaded.name}_{uploaded.size}"
            if st.session_state.last_upload_key != fkey:
                st.session_state.last_upload_key = fkey
                os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)
                dest = os.path.join(KNOWLEDGE_BASE_DIR, uploaded.name)
                with open(dest, "wb") as fh:
                    fh.write(uploaded.getbuffer())
                res = _ingest(dest, uploaded.name)
                # Flash mesajı: 2 saniye görünür
                expiry = time.time() + 2.0
                if res["ok"]:
                    msg = t("upload_ok", f=uploaded.name, n=res["chunks"])
                    st.session_state.upload_flash = [(True, msg, expiry)]
                else:
                    msg = t("upload_err", f=uploaded.name, e=res["error"])
                    st.session_state.upload_flash = [(False, msg, expiry)]
                # Uploader'ı sıfırla
                st.session_state.uploader_key_idx += 1
                st.rerun()

        # Flash mesajları
        now = time.time()
        active_flash = [(ok, msg, exp) for (ok, msg, exp) in st.session_state.upload_flash if exp > now]
        st.session_state.upload_flash = active_flash
        for ok, msg, _ in active_flash:
            if ok:
                st.success(msg)
            else:
                st.error(msg)

        # ── İndekslenen Dokümanlar ───────────────────────
        st.markdown(f"""
        <div class="s-card" style="margin-top:0.4rem; padding-bottom: 0.3rem;">
            <div class="s-label">{t("indexed_docs")}</div>
        </div>
        """, unsafe_allow_html=True)

        try:
            from db.manager import get_sources, get_chunk_count, clear_source
            sources = get_sources()
            chunk_count = get_chunk_count()

            if sources:
                with st.container(height=230):
                    for src in sources:
                        icon = "📕" if src.endswith(".pdf") else "📄"
                        cols = st.columns([5, 1, 1])
                        with cols[0]:
                            st.markdown(
                                f'<div class="doc-item-name" title="{src}">{icon} {src}</div>',
                                unsafe_allow_html=True,
                            )
                        with cols[1]:
                            if st.button(t("prv_btn"), key=f"prv_{src}", help=f"Önizle: {src}"):
                                st.session_state.preview_doc = src
                                st.rerun()
                        with cols[2]:
                            if st.button(t("del_btn"), key=f"del_{src}", help=f"Sil: {src}"):
                                clear_source(src)
                                if st.session_state.preview_doc == src:
                                    st.session_state.preview_doc = None
                                st.rerun()

                st.markdown(
                    f'<div class="doc-count-footer">{t("total_docs", n=len(sources), c=chunk_count)}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption(t("no_docs"))
        except Exception as e:
            st.caption(f"DB hatası: {e}")

        # ── Alt Sabit Alan (Sohbeti Temizle) ───────────────
        st.markdown('<div class="sidebar-bottom"><div class="clear-chat-container">', unsafe_allow_html=True)
        if st.button(t("clear_chat"), key="clear_chat_btn", width="stretch"):
            st.session_state.messages = []
            st.session_state.pending_question = None
            st.rerun()
        st.markdown(
            f'</div><div class="privacy-note">{t("privacy")}</div></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Önizleme
# ---------------------------------------------------------------------------
def render_preview() -> None:
    doc = st.session_state.get("preview_doc")
    if not doc:
        return
    with st.expander(f"📖 {t('preview_title')}: {doc}", expanded=True):
        content = _preview_text(doc)
        st.text_area("preview_content", value=content, height=280, disabled=True, label_visibility="collapsed")
        if st.button(t("preview_close"), key="close_prev"):
            st.session_state.preview_doc = None
            st.rerun()


# ---------------------------------------------------------------------------
# Chat Render & Starter Prompts
# ---------------------------------------------------------------------------
def _format_message_body_html(text: str) -> str:
    """
    Markdown metinlerini güvenle HTML'e dönüştürür.
    """
    if not text:
        return ""
    safe = html.escape(text)
    # **kalın** -> <strong>kalın</strong>
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    # *italik* -> <em>italik</em>
    safe = re.sub(r"\*(.+?)\*", r"<em>\1</em>", safe)
    # `kod` -> <code style="...">kod</code>
    safe = re.sub(
        r"`(.+?)`",
        r'<code style="background:rgba(0,0,0,0.06);padding:2px 5px;border-radius:4px;font-size:0.88em;">\1</code>',
        safe,
    )

    lines = safe.split("\n")
    formatted = []
    in_list = False
    list_type = "ul"

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                formatted.append(f"</{list_type}>")
                in_list = False
            formatted.append('<div style="height:0.4rem;"></div>')
            continue

        # Başlıklar
        if stripped.startswith("### "):
            if in_list:
                formatted.append(f"</{list_type}>")
                in_list = False
            formatted.append(
                f'<div style="font-weight:700;font-size:1.02rem;margin:0.5rem 0 0.25rem 0;color:#0F172A;">{stripped[4:]}</div>'
            )
        elif stripped.startswith("## "):
            if in_list:
                formatted.append(f"</{list_type}>")
                in_list = False
            formatted.append(
                f'<div style="font-weight:700;font-size:1.08rem;margin:0.6rem 0 0.3rem 0;color:#0F172A;">{stripped[3:]}</div>'
            )
        elif stripped.startswith("# "):
            if in_list:
                formatted.append(f"</{list_type}>")
                in_list = False
            formatted.append(
                f'<div style="font-weight:700;font-size:1.18rem;margin:0.7rem 0 0.35rem 0;color:#0F172A;">{stripped[2:]}</div>'
            )
        # Madde imleri (- veya * veya •)
        elif stripped.startswith(("- ", "* ", "• ")):
            if not in_list or list_type != "ul":
                if in_list:
                    formatted.append(f"</{list_type}>")
                formatted.append('<ul style="margin:0.35rem 0;padding-left:1.3rem;line-height:1.65;">')
                in_list = True
                list_type = "ul"
            item = stripped[2:].strip()
            formatted.append(f'<li style="margin-bottom:0.3rem;">{item}</li>')
        # Numaralı liste (1. 2. vb.)
        elif re.match(r"^\d+\.\s+", stripped):
            if not in_list or list_type != "ol":
                if in_list:
                    formatted.append(f"</{list_type}>")
                formatted.append('<ol style="margin:0.35rem 0;padding-left:1.3rem;line-height:1.65;">')
                in_list = True
                list_type = "ol"
            item = re.sub(r"^\d+\.\s+", "", stripped).strip()
            formatted.append(f'<li style="margin-bottom:0.3rem;">{item}</li>')
        else:
            if in_list:
                formatted.append(f"</{list_type}>")
                in_list = False
            formatted.append(f'<p style="margin:0.35rem 0;line-height:1.65;">{stripped}</p>')

    if in_list:
        formatted.append(f"</{list_type}>")

    return "".join(formatted)


def render_welcome_and_starter_questions() -> None:
    """Chat geçmişi boşken ferah karşılama ekranı ve tıklanabilir örnek soru kartları sunar."""
    st.markdown(f"""
    <div class="welcome-container">
        <div class="welcome-title">💡 {t("welcome_title")}</div>
        <div class="welcome-subtitle">{t("welcome_subtitle")}</div>
    </div>
    """, unsafe_allow_html=True)

    starter_questions = [
        ("☕ " + t("starter_q1"), t("starter_q1")),
        ("🛡️ " + t("starter_q2"), t("starter_q2")),
        ("⚡ " + t("starter_q3"), t("starter_q3")),
        ("🔍 " + t("starter_q4"), t("starter_q4")),
    ]

    col1, col2 = st.columns(2)
    for idx, (display_text, actual_question) in enumerate(starter_questions):
        target_col = col1 if idx % 2 == 0 else col2
        with target_col:
            st.markdown('<div class="starter-card-wrapper">', unsafe_allow_html=True)
            if st.button(display_text, key=f"starter_btn_{idx}", width="stretch"):
                st.session_state.messages.append({"role": "user", "content": actual_question})
                st.session_state.pending_question = actual_question
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


def render_messages() -> None:
    if not st.session_state.messages and not st.session_state.pending_question:
        render_welcome_and_starter_questions()
        return

    for msg in st.session_state.messages:
        role    = msg["role"]
        content = msg["content"]
        sources = msg.get("sources", [])
        latency = msg.get("latency", "")

        if role == "user":
            safe_content = html.escape(content).replace("\n", "<br>")
            user_html = (
                '<div class="msg-user">'
                f'<div class="bubble">{safe_content}</div>'
                '<div class="user-av">👤</div>'
                '</div>'
            )
            st.markdown(user_html, unsafe_allow_html=True)
        else:
            body_html = _format_message_body_html(content)
            src_html = ""
            if sources:
                chips = "".join(f'<span class="src-chip">📄 {html.escape(s)}</span>' for s in sources)
                src_html = (
                    '<div class="src-row">'
                    f'<span style="font-weight:600;">{t("src_label")}</span>'
                    f'<div class="src-chips">{chips}</div>'
                    '</div>'
                )

            lat_tag = f'<span class="latency-tag">{html.escape(latency)}</span>' if latency else ""
            bot_html = (
                '<div class="msg-bot">'
                '<div class="bot-meta">'
                '<div class="bot-av">🤖</div>'
                f'{lat_tag}'
                '</div>'
                f'<div class="bubble"><div>{body_html}</div>{src_html}</div>'
                '</div>'
            )
            st.markdown(bot_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Ana Akış
# ---------------------------------------------------------------------------
def main():
    _init()

    # Pipeline yükle
    try:
        with st.spinner(t("loading")):
            pipeline = _load_pipeline()
            st.session_state.pipeline = pipeline
            st.session_state.pipeline_status = "ready"
            st.session_state.error_message = None
    except Exception as e:
        st.session_state.pipeline_status = "error"
        st.session_state.error_message = str(e)

    pipeline_ready = st.session_state.pipeline_status == "ready"

    render_sidebar()

    if not pipeline_ready:
        st.error(f"{t('err_loading')}: {st.session_state.error_message}")
        st.info(t("err_check"))
        return

    render_preview()

    # --- Aşama 1: Geçmiş / Başlangıç sorularını göster ---
    render_messages()

    # --- Aşama 2: Bekleyen soru varsa işle ---
    if st.session_state.pending_question:
        question = st.session_state.pending_question
        with st.spinner(t("searching")):
            t0 = time.time()
            try:
                pip = st.session_state.pipeline
                history = [m for m in st.session_state.messages if m["role"] != "assistant" or m != st.session_state.messages[-1]]
                response = pip.ask(question, chat_history=st.session_state.messages[:-1])
                elapsed = time.time() - t0
                lat = f"{elapsed:.1f}s"

                if response.has_error:
                    bot_content = f"❌ {t('err_generic')}: {response.error}"
                    sources = []
                else:
                    bot_content = response.answer
                    sources = response.unique_sources
            except Exception as e:
                bot_content = f"❌ {t('err_generic')}: {e}"
                sources = []
                lat = ""

        st.session_state.messages.append({
            "role":    "assistant",
            "content": bot_content,
            "sources": sources,
            "latency": lat,
        })
        st.session_state.pending_question = None
        st.rerun()

    # --- Aşama 3: Kullanıcı girdisini al ---
    prompt = st.chat_input(
        placeholder=t("placeholder"),
        disabled=not pipeline_ready,
    )
    if prompt and prompt.strip():
        question = prompt.strip()
        st.session_state.messages.append({"role": "user", "content": question})
        st.session_state.pending_question = question
        st.rerun()


if __name__ == "__main__":
    main()
