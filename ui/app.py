"""
ui/app.py — Local RAG Asistanı (Profesyonel Light UI/UX)
=========================================================
Görsel referansa birebir uygun, Türkçe/İngilizce dil desteği,
sabit sidebar alt menü, kaydırmalı doküman listesi, anlık önizleme.

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
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Dil Sözlüğü
# ---------------------------------------------------------------------------
LANG = {
    "tr": {
        "app_title":      "Local RAG Asistanı",
        "sys_status":     "SİSTEM DURUMU",
        "models_ready":   "Modeller Hazır (Yerel)",
        "doc_upload":     "DOKÜMAN YÜKLE",
        "upload_hint":    ".txt, .md veya .pdf yükleyin",
        "indexed_docs":   "İNDEKSLENEN DOKÜMANLAR",
        "no_docs":        "Henüz doküman yüklenmedi.",
        "total_docs":     "{n} doküman · {c} parça",
        "clear_chat":     "🗑️ Sohbeti Temizle",
        "privacy":        "🔒 Verileriniz cihazınızdan asla çıkmaz",
        "placeholder":    "Dokümanlarınız hakkında soru sorun...",
        "searching":      "Yanıt aranıyor...",
        "loading":        "Modeller yükleniyor...",
        "err_loading":    "Model yükleme hatası",
        "err_check":      "Foundry Local'in çalıştığını kontrol edin.",
        "err_no_docs":    "İndekslenmiş doküman yok. Lütfen soldaki panelden doküman yükleyin.",
        "err_generic":    "Beklenmedik hata",
        "src_label":      "Kaynak:",
        "preview_title":  "Doküman Önizlemesi",
        "preview_close":  "Kapat",
        "upload_ok":      "✓ {f} ({n} parça eklendi)",
        "upload_err":     "✕ {f}: {e}",
        "lang_label":     "🌐 Dil",
        "del_btn":        "✕",
        "prv_btn":        "👁",
    },
    "en": {
        "app_title":      "Local RAG Assistant",
        "sys_status":     "SYSTEM STATUS",
        "models_ready":   "Models Ready (Local)",
        "doc_upload":     "DOCUMENT UPLOAD",
        "upload_hint":    "Upload .txt, .md or .pdf",
        "indexed_docs":   "INDEXED DOCUMENTS",
        "no_docs":        "No documents indexed yet.",
        "total_docs":     "{n} docs · {c} chunks",
        "clear_chat":     "🗑️ Clear Chat",
        "privacy":        "🔒 Your data never leaves this device",
        "placeholder":    "Ask about your documents...",
        "searching":      "Searching...",
        "loading":        "Loading models...",
        "err_loading":    "Model loading error",
        "err_check":      "Check that Foundry Local is running.",
        "err_no_docs":    "No indexed documents. Please upload from the left panel.",
        "err_generic":    "Unexpected error",
        "src_label":      "Source:",
        "preview_title":  "Document Preview",
        "preview_close":  "Close",
        "upload_ok":      "✓ {f} ({n} chunks added)",
        "upload_err":     "✕ {f}: {e}",
        "lang_label":     "🌐 Language",
        "del_btn":        "✕",
        "prv_btn":        "👁",
    },
}

def t(key: str, **kwargs) -> str:
    lang = st.session_state.get("lang", "tr")
    text = LANG.get(lang, LANG["tr"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


# ---------------------------------------------------------------------------
# Tüm CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, sans-serif !important;
    background-color: #F0F4F8 !important;
    color: #1E293B !important;
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
    padding: 0.75rem 0.75rem !important;
    display: flex !important;
    flex-direction: column !important;
    height: 100vh !important;
    overflow: hidden !important;
    gap: 0 !important;
}

/* Başlık */
.panel-brand {
    font-size: 0.93rem;
    font-weight: 700;
    color: #1E293B;
    padding: 0.2rem 0 0.55rem 0;
    border-bottom: 1px solid #D1DCE8;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-bottom: 0.45rem;
    flex-shrink: 0;
}

/* Kart */
.s-card {
    background: #FFFFFF;
    border: 1px solid #D8E2EC;
    border-radius: 9px;
    padding: 0.55rem 0.75rem;
    margin-bottom: 0.4rem;
    flex-shrink: 0;
}
.s-label {
    font-size: 0.67rem;
    font-weight: 700;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 0.35rem;
}

/* Sistem durumu */
.status-ok {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.84rem;
    font-weight: 500;
    color: #16A34A;
}
.dot-green { width: 8px; height: 8px; background: #22C55E; border-radius: 50%; }

/* Dosya yükleyici */
[data-testid="stFileUploader"] {
    background-color: #F8FAFC !important;
    border: 1.5px dashed #93C5FD !important;
    border-radius: 8px !important;
}
[data-testid="stFileUploader"] section {
    background-color: transparent !important;
    border: none !important;
}
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] p { color: #475569 !important; }
[data-testid="stFileUploader"] button {
    background: #FFF !important;
    color: #1E293B !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 5px !important;
    font-size: 0.78rem !important;
}

/* İndekslenen dokümanlar kartı içi */
.doc-list-inner {
    max-height: 175px;
    overflow-y: auto;
    overflow-x: hidden;
    margin: 0 -0.1rem;
}
.doc-list-inner::-webkit-scrollbar { width: 3px; }
.doc-list-inner::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 2px; }

.doc-item-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.28rem 0.1rem;
    border-bottom: 1px solid #EEF2F6;
    gap: 0.3rem;
}
.doc-item-row:last-child { border-bottom: none; }
.doc-item-name {
    font-size: 0.8rem;
    color: #334155;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
}
.doc-count-footer {
    font-size: 0.72rem;
    color: #64748B;
    margin-top: 0.35rem;
    padding-top: 0.3rem;
    border-top: 1px solid #E2E8F0;
}

/* Doc action butonları — küçük */
[data-testid="stSidebar"] .stButton button {
    padding: 0.1rem 0.35rem !important;
    min-height: unset !important;
    font-size: 0.72rem !important;
    line-height: 1.4 !important;
}

/* Esnek boşluk ve alt alan */
.flex-grow { flex: 1 1 auto; }
.sidebar-bottom {
    flex-shrink: 0;
    padding-top: 0.4rem;
    border-top: 1px solid #D1DCE8;
    margin-top: 0.4rem;
}
.privacy-note {
    font-size: 0.72rem;
    color: #64748B;
    text-align: center;
    margin-top: 0.3rem;
}
[data-testid="stSidebar"] .stButton > button[data-testid*="clear"] {
    width: 100% !important;
}

/* Flash mesajı 2 saniyede kaybolma efekti */
[data-testid="stSidebar"] [data-testid="stAlert"] {
    animation: flashFadeOut 0.5s ease 2s forwards;
}
@keyframes flashFadeOut {
    0% { opacity: 1; }
    99% { opacity: 0; max-height: 0; margin: 0; padding: 0; }
    100% { opacity: 0; display: none; max-height: 0; margin: 0; padding: 0; }
}

/* Dil radio */
[data-testid="stRadio"] > div { flex-direction: row !important; gap: 0.6rem !important; }
[data-testid="stRadio"] label { font-size: 0.82rem !important; }

/* ── Chat Mesajları ──────────────────────────────── */
/* Kullanıcı → SAĞ */
.msg-user {
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
    gap: 0.55rem;
    margin: 0.9rem 0;
}
.msg-user .bubble {
    background: #E2E8F0;
    color: #0F172A;
    padding: 0.75rem 1rem;
    border-radius: 14px 14px 4px 14px;
    font-size: 0.91rem;
    line-height: 1.55;
    max-width: 72%;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    word-break: break-word;
}
.user-av {
    width: 33px; height: 33px;
    border-radius: 50%;
    background: #CBD5E1;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.95rem; flex-shrink: 0;
}

/* Asistan → SOL */
.msg-bot {
    display: flex;
    justify-content: flex-start;
    align-items: flex-start;
    gap: 0.55rem;
    margin: 0.9rem 0;
}
.msg-bot .bubble {
    background: #E0EDFB;
    border: 1px solid #BED8F3;
    color: #0F172A;
    padding: 0.85rem 1.1rem;
    border-radius: 14px 14px 14px 4px;
    font-size: 0.91rem;
    line-height: 1.6;
    max-width: 76%;
    box-shadow: 0 2px 5px rgba(0,0,0,0.04);
    word-break: break-word;
}
.bot-meta {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.1rem;
    flex-shrink: 0;
}
.bot-av {
    width: 33px; height: 33px;
    border-radius: 9px;
    background: #E0F2FE;
    border: 1px solid #BAE6FD;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem;
}
.latency-tag {
    font-size: 0.66rem;
    color: #64748B;
    font-weight: 500;
}

/* Kaynak satırı */
.src-row {
    margin-top: 0.65rem;
    padding-top: 0.5rem;
    border-top: 1px solid #C4DCF3;
    font-size: 0.76rem;
    color: #475569;
}
.src-chips { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.2rem; }
.src-chip {
    background: rgba(37,99,235,0.08);
    border: 1px solid rgba(37,99,235,0.2);
    color: #1D4ED8;
    padding: 0.12rem 0.45rem;
    border-radius: 4px;
    font-size: 0.73rem;
    font-weight: 500;
}

/* Chat input */
[data-testid="stChatInput"] {
    background: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 14px !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.05) !important;
    max-width: 860px !important;
    margin: 0 auto !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: #3B82F6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: #1E293B !important;
    font-size: 0.9rem !important;
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
        "selected_model":     "qwen3-1.7b",   # Varsayılan: en hızlı model
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
        # Marka başlığı
        st.markdown(
            f'<div class="panel-brand">🧠 {t("app_title")}</div>',
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

        # ── Model Seçici ─────────────────────────────────
        models_list = getattr(config, "AVAILABLE_LLM_MODELS", [
            ("qwen3-1.7b",   "Qwen3-1.7B  ⚡ (Hızlı ~8-15sn, 1.4GB)"),
            ("qwen3-4b",     "Qwen3-4B   ⚡⚡ (Dengeli ~20-35sn, 2.8GB)"),
            ("phi-3.5-mini", "Phi-3.5-mini  (Yavaş ~30-60sn, 2.6GB)"),
        ])
        model_aliases  = [alias for alias, _ in models_list]
        model_labels   = [label for _, label in models_list]
        current_idx    = model_aliases.index(st.session_state.selected_model) \
                         if st.session_state.selected_model in model_aliases else 0
        label_txt = "🤖 Model" if st.session_state.lang == "tr" else "🤖 Model"
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
        current_model = st.session_state.selected_model
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
        <div class="s-card" style="margin-bottom:0.1rem;">
            <div class="s-label">{t("doc_upload")}</div>
        </div>
        """, unsafe_allow_html=True)

        uploader_key = f"uploader_{st.session_state.uploader_key_idx}"
        uploaded = st.file_uploader(
            label="upload",
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
                # Uploader'ı sıfırla (key değiştirerek widget unmount edilir)
                st.session_state.uploader_key_idx += 1
                st.rerun()

        # Flash mesajları (2s sonra kaybolur)
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
        <div class="s-card" style="margin-top:0.4rem;">
            <div class="s-label">{t("indexed_docs")}</div>
            <div class="doc-list-inner" id="doc-list-scroll">
        """, unsafe_allow_html=True)

        try:
            from db.manager import get_sources, get_chunk_count, clear_source
            sources = get_sources()
            chunk_count = get_chunk_count()

            if sources:
                for src in sources:
                    icon = "📕" if src.endswith(".pdf") else "📄"
                    # Her satır: isim + butonlar
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

        # Kart kapanışı (doc-list-inner + s-card)
        st.markdown("</div></div>", unsafe_allow_html=True)

        # Esnek boşluk — alt alanı iter
        st.markdown('<div class="flex-grow"></div>', unsafe_allow_html=True)

        # ── Alt Sabit Alan ────────────────────────────────
        st.markdown('<div class="sidebar-bottom">', unsafe_allow_html=True)
        if st.button(t("clear_chat"), key="clear_chat_btn", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pending_question = None
            st.rerun()
        st.markdown(
            f'<div class="privacy-note">{t("privacy")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


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
# Chat Render
# ---------------------------------------------------------------------------
def _format_message_body_html(text: str) -> str:
    """
    Markdown metinlerini (başlıklar, kalın/italik, madde imleri, paragraflar)
    HTML içine güvenle gömer. Streamlit'in 4-boşluk kod bloğu sorununu önler.
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
        r'<code style="background:rgba(0,0,0,0.06);padding:2px 4px;border-radius:4px;font-size:0.85em;">\1</code>',
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
            formatted.append('<div style="height:0.35rem;"></div>')
            continue

        # Başlıklar
        if stripped.startswith("### "):
            if in_list:
                formatted.append(f"</{list_type}>")
                in_list = False
            formatted.append(
                f'<div style="font-weight:700;font-size:0.95rem;margin:0.4rem 0 0.2rem 0;color:#0F172A;">{stripped[4:]}</div>'
            )
        elif stripped.startswith("## "):
            if in_list:
                formatted.append(f"</{list_type}>")
                in_list = False
            formatted.append(
                f'<div style="font-weight:700;font-size:1.02rem;margin:0.5rem 0 0.25rem 0;color:#0F172A;">{stripped[3:]}</div>'
            )
        elif stripped.startswith("# "):
            if in_list:
                formatted.append(f"</{list_type}>")
                in_list = False
            formatted.append(
                f'<div style="font-weight:700;font-size:1.1rem;margin:0.6rem 0 0.3rem 0;color:#0F172A;">{stripped[2:]}</div>'
            )
        # Madde imleri (- veya * veya •)
        elif stripped.startswith(("- ", "* ", "• ")):
            if not in_list or list_type != "ul":
                if in_list:
                    formatted.append(f"</{list_type}>")
                formatted.append('<ul style="margin:0.3rem 0;padding-left:1.2rem;line-height:1.55;">')
                in_list = True
                list_type = "ul"
            item = stripped[2:].strip()
            formatted.append(f'<li style="margin-bottom:0.25rem;">{item}</li>')
        # Numaralı liste (1. 2. vb.)
        elif re.match(r"^\d+\.\s+", stripped):
            if not in_list or list_type != "ol":
                if in_list:
                    formatted.append(f"</{list_type}>")
                formatted.append('<ol style="margin:0.3rem 0;padding-left:1.2rem;line-height:1.55;">')
                in_list = True
                list_type = "ol"
            item = re.sub(r"^\d+\.\s+", "", stripped).strip()
            formatted.append(f'<li style="margin-bottom:0.25rem;">{item}</li>')
        else:
            if in_list:
                formatted.append(f"</{list_type}>")
                in_list = False
            formatted.append(f'<p style="margin:0.3rem 0;line-height:1.55;">{stripped}</p>')

    if in_list:
        formatted.append(f"</{list_type}>")

    return "".join(formatted)


def render_messages() -> None:
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

    # --- Aşama 1: Geçmiş + bekleyen soruyu göster ---
    render_messages()

    # --- Aşama 2: Bekleyen soru varsa işle (spinner BURADA, mesajdan SONRA) ---
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
        # Önce kullanıcı mesajını kaydet ve ekrana göster (rerun ile)
        st.session_state.messages.append({"role": "user", "content": question})
        st.session_state.pending_question = question
        st.rerun()


if __name__ == "__main__":
    main()
