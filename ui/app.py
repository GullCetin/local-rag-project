"""
ui/app.py - Local RAG Asistani (Kurumsal UI)
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
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Dil Sözlüğü
# ---------------------------------------------------------------------------
LANG = {
    "tr": {
        "app_title":        "RAG Asistanı",
        "app_subtitle":     "Kurumsal Belge Zekası",
        "sys_status":       "Sistem",
        "models_ready":     "Çevrimdışı — Veriler cihazda",
        "model_label":      "Yanıt Modeli",
        "doc_upload":       "Belge Ekle",
        "upload_btn":       "Dosya Seç",
        "upload_hint":      ".txt · .md · .pdf",
        "indexed_docs":     "İndekslenmiş Belgeler",
        "no_docs":          "Henüz belge eklenmedi.",
        "total_docs":       "{n} belge · {c} parça",
        "clear_chat":       "Sohbeti Temizle",
        "privacy":          "100% Yerel · Sıfır Veri Çıkışı",
        "placeholder":      "Belgeleriniz hakkında soru sorun...",
        "searching":        "Yanıt aranıyor...",
        "loading":          "Modeller yükleniyor...",
        "err_loading":      "Model yükleme hatası",
        "err_check":        "Foundry Local'in çalıştığını kontrol edin.",
        "err_no_docs":      "İndekslenmiş belge yok. Lütfen sol panelden belge ekleyin.",
        "err_generic":      "Beklenmedik hata",
        "src_label":        "Kaynaklar",
        "preview_title":    "Belge Önizlemesi",
        "preview_close":    "Kapat",
        "upload_ok":        "{f} — {n} parça indekslendi",
        "upload_err":       "{f}: {e}",
        "lang_label":       "Dil",
        "del_btn":          "Sil",
        "prv_btn":          "Önizle",
        "welcome_title":    "Belgelerinize sorun.",
        "welcome_subtitle": "Yüklediğiniz dokümanlar hakkında doğal dilde soru sorabilirsiniz.",
        "chunks_label":     "parça",
        "model_switching":  "Model değiştiriliyor...",
        "ai_label":         "RAG Asistanı",
    },
    "en": {
        "app_title":        "RAG Assistant",
        "app_subtitle":     "Enterprise Document Intelligence",
        "sys_status":       "System",
        "models_ready":     "Offline — Data on device",
        "model_label":      "Response Model",
        "doc_upload":       "Add Document",
        "upload_btn":       "Select File",
        "upload_hint":      ".txt · .md · .pdf",
        "indexed_docs":     "Indexed Documents",
        "no_docs":          "No documents added yet.",
        "total_docs":       "{n} docs · {c} chunks",
        "clear_chat":       "Clear Chat",
        "privacy":          "100% Local · Zero Data Egress",
        "placeholder":      "Ask about your documents...",
        "searching":        "Searching for answer...",
        "loading":          "Loading models...",
        "err_loading":      "Model loading error",
        "err_check":        "Check that Foundry Local is running.",
        "err_no_docs":      "No indexed documents. Please add from the left panel.",
        "err_generic":      "Unexpected error",
        "src_label":        "Sources",
        "preview_title":    "Document Preview",
        "preview_close":    "Close",
        "upload_ok":        "{f} — {n} chunks indexed",
        "upload_err":       "{f}: {e}",
        "lang_label":       "Language",
        "del_btn":          "Delete",
        "prv_btn":          "Preview",
        "welcome_title":    "Ask about your documents.",
        "welcome_subtitle": "Ask questions in natural language about your indexed documents.",
        "chunks_label":     "chunks",
        "model_switching":  "Switching model...",
        "ai_label":         "RAG Assistant",
    },
}


def t(key: str, **kwargs) -> str:
    lang = st.session_state.get("lang", "tr")
    text = LANG.get(lang, LANG["tr"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, .stApp, [class*="css"],
p, label, input, textarea, button, div, span {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}
html, body, .stApp {
    background-color: #F7F8FA !important;
    color: #111827 !important;
    font-size: 15px !important;
    line-height: 1.6 !important;
    letter-spacing: -0.01em !important;
    -webkit-font-smoothing: antialiased !important;
}
header[data-testid="stHeader"] {
    background-color: rgba(247,248,250,0.92) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border-bottom: 1px solid rgba(0,0,0,0.06) !important;
}
#MainMenu, footer, [data-testid="stDecoration"],
[data-testid="stToolbar"] { display: none !important; }

[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid rgba(0,0,0,0.07) !important;
    box-shadow: 2px 0 16px rgba(0,0,0,0.03) !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 1.25rem 1.1rem !important;
    display: flex !important;
    flex-direction: column !important;
    height: 100vh !important;
    overflow-y: auto !important;
    gap: 0.3rem !important;
}
.sb-brand { padding: 0 0 0.9rem 0; border-bottom: 1px solid #F3F4F6; margin-bottom: 0.2rem; }
.sb-brand-title { font-size: 1rem; font-weight: 700; color: #111827; letter-spacing: -0.03em; }
.sb-brand-sub { font-size: 0.7rem; color: #9CA3AF; font-weight: 400; margin-top: 0.1rem; }
.sb-section-label {
    font-size: 0.67rem; font-weight: 600; color: #9CA3AF;
    text-transform: uppercase; letter-spacing: 0.07em; margin: 0.8rem 0 0.35rem 0;
}
.sb-status-pill {
    display: inline-flex; align-items: center; gap: 0.4rem;
    background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 99px;
    padding: 0.28rem 0.65rem; font-size: 0.76rem; font-weight: 500; color: #15803D;
}
.sb-dot { width: 6px; height: 6px; background: #22C55E; border-radius: 50%; flex-shrink: 0; }

[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
    background: #F9FAFB !important; border: 1px solid #E5E7EB !important;
    border-radius: 8px !important; font-size: 0.83rem !important; color: #111827 !important;
}
[data-testid="stFileUploader"] {
    background: #F9FAFB !important; border: 1.5px dashed #D1D5DB !important; border-radius: 10px !important;
}
[data-testid="stFileUploader"] section { border: none !important; background: transparent !important; }
[data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
[data-testid="stFileUploader"] button {
    background: #F3F4F6 !important; color: #374151 !important;
    border: 1px solid #E5E7EB !important; border-radius: 7px !important;
    font-size: 0.81rem !important; font-weight: 500 !important;
    padding: 0.3rem 0.7rem !important; transition: all 0.15s ease !important;
}
[data-testid="stFileUploader"] button:hover { background: #E9EAEC !important; }

.doc-row { display: flex; align-items: center; padding: 0.4rem 0.2rem; border-bottom: 1px solid #F9FAFB; gap: 0.4rem; }
.doc-row:last-child { border-bottom: none; }
.doc-name { font-size: 0.8rem; color: #374151; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.doc-chunks { font-size: 0.7rem; color: #9CA3AF; flex-shrink: 0; }
.doc-count-bar { font-size: 0.73rem; color: #6B7280; padding-top: 0.45rem; border-top: 1px solid #F3F4F6; margin-top: 0.2rem; }

[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
    font-size: 0.78rem !important; padding: 0.2rem 0.45rem !important;
    border-radius: 6px !important; background: transparent !important;
    border: 1px solid #E5E7EB !important; color: #6B7280 !important;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {
    background: #F3F4F6 !important; color: #111827 !important; border-color: #D1D5DB !important;
}
div.sb-clear-btn button {
    background: transparent !important; color: #EF4444 !important;
    border: none !important; font-size: 0.83rem !important; font-weight: 500 !important;
    padding: 0.45rem 0.5rem !important; border-radius: 7px !important;
    width: 100% !important; transition: all 0.15s ease !important; box-shadow: none !important;
}
div.sb-clear-btn button:hover { background: #FEF2F2 !important; color: #DC2626 !important; }

.sb-footer { border-top: 1px solid #F3F4F6; padding-top: 0.65rem; margin-top: 0.5rem; }
.sb-privacy { font-size: 0.69rem; color: #9CA3AF; text-align: center; }

[data-testid="stSidebar"] [data-testid="stAlert"] {
    animation: sbFade 0.4s ease 2.5s forwards;
    border-radius: 8px !important; border: none !important; font-size: 0.8rem !important;
}
@keyframes sbFade { to { opacity:0; max-height:0; margin:0; padding:0; overflow:hidden; } }

[data-testid="stRadio"] > div { flex-direction: row !important; gap: 0.65rem !important; }
[data-testid="stRadio"] label { font-size: 0.8rem !important; font-weight: 400 !important; }

.welcome-wrap {
    text-align: center; padding: 3.5rem 1rem 1.5rem 1rem;
    max-width: 620px; margin: 0 auto;
}
.welcome-icon { font-size: 2rem; margin-bottom: 0.9rem; opacity: 0.8; }
.welcome-title {
    font-size: 1.6rem; font-weight: 700; color: #111827;
    letter-spacing: -0.03em; margin-bottom: 0.5rem; line-height: 1.25;
}
.welcome-subtitle { font-size: 0.92rem; color: #6B7280; line-height: 1.55; margin-bottom: 2rem; }

div.starter-wrapper button {
    background: #FFFFFF !important; border: 1px solid #E5E7EB !important;
    border-radius: 12px !important; padding: 0.9rem 1rem !important;
    font-size: 0.86rem !important; font-weight: 400 !important;
    color: #374151 !important; text-align: left !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
    transition: all 0.16s ease !important;
    min-height: 72px !important; line-height: 1.45 !important; width: 100% !important;
}
div.starter-wrapper button:hover {
    border-color: #2563EB !important; box-shadow: 0 4px 16px rgba(37,99,235,0.1) !important;
    transform: translateY(-1px); color: #1D4ED8 !important;
}

.msg-user-wrap { display: flex; justify-content: flex-end; margin: 1.1rem 0 0.4rem 0; }
.msg-user-pill {
    background: #EFF6FF; border: 1px solid #BFDBFE; color: #1E40AF;
    font-size: 0.93rem; font-weight: 500;
    padding: 0.55rem 0.95rem; border-radius: 12px 12px 3px 12px;
    max-width: 70%; word-break: break-word; line-height: 1.5;
}

.msg-bot-wrap { margin: 0.4rem 0 1.4rem 0; }
.msg-bot-header { display: flex; align-items: center; gap: 0.45rem; margin-bottom: 0.45rem; }
.msg-bot-icon {
    width: 20px; height: 20px; background: #2563EB; border-radius: 5px;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    font-size: 0.65rem; color: #fff; font-weight: 700; letter-spacing: -0.01em;
}
.msg-bot-label { font-size: 0.76rem; font-weight: 600; color: #374151; }
.msg-bot-card {
    background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 14px;
    padding: 1rem 1.2rem; box-shadow: 0 1px 6px rgba(0,0,0,0.04);
}
.msg-bot-body { font-size: 0.93rem; color: #111827; line-height: 1.7; }
.msg-bot-body p { margin: 0.25rem 0; }
.msg-bot-body ul, .msg-bot-body ol { margin: 0.35rem 0; padding-left: 1.3rem; }
.msg-bot-body li { margin-bottom: 0.2rem; line-height: 1.65; }
.msg-bot-body strong { color: #111827; font-weight: 600; }

.src-section {
    margin-top: 0.85rem; padding-top: 0.7rem; border-top: 1px solid #F3F4F6;
    display: flex; align-items: flex-start; gap: 0.55rem; flex-wrap: wrap;
}
.src-section-label {
    font-size: 0.7rem; font-weight: 600; color: #9CA3AF;
    text-transform: uppercase; letter-spacing: 0.05em; padding-top: 0.15rem; flex-shrink: 0;
}
.src-chips { display: flex; flex-wrap: wrap; gap: 0.3rem; }
.src-chip {
    background: #F3F4F6; border: 1px solid #E5E7EB; color: #374151;
    padding: 0.18rem 0.5rem; border-radius: 5px; font-size: 0.73rem; font-weight: 500;
}

.msg-meta-row { display: flex; align-items: center; gap: 0.6rem; margin-top: 0.5rem; }
.msg-meta-item { font-size: 0.7rem; color: #9CA3AF; }
.msg-meta-sep { color: #E5E7EB; }

[data-testid="stChatInput"] {
    background: #FFFFFF !important; border: 1.5px solid #E5E7EB !important;
    border-radius: 14px !important; box-shadow: 0 2px 12px rgba(0,0,0,0.06) !important;
    max-width: 820px !important; margin: 0 auto !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: #2563EB !important; box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important; color: #111827 !important;
    font-size: 0.93rem !important; padding: 0.6rem 1rem !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #9CA3AF !important; }
[data-testid="stChatInput"] button {
    background: #2563EB !important; color: #FFF !important;
    border-radius: 9px !important; border: none !important;
    width: 32px !important; height: 32px !important;
    margin-right: 0.4rem !important; transition: all 0.15s ease !important;
}
[data-testid="stChatInput"] button:hover { background: #1D4ED8 !important; }

[data-testid="stExpander"] {
    background: #FFFFFF !important; border: 1px solid #E5E7EB !important;
    border-radius: 12px !important; margin-bottom: 1rem !important;
}
[data-testid="stSpinner"] { font-size: 0.86rem !important; color: #6B7280 !important; }
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
        "selected_model":     getattr(config, "LLM_MODEL_ALIAS", "qwen3-1.7b"),
        "switching_model":    False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


@st.cache_resource(show_spinner=False)
def _load_pipeline():
    from rag.pipeline import RAGPipeline
    p = RAGPipeline()
    p.load()
    return p


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


def _preview_text(source_name: str, max_chars: int = 3000) -> str:
    try:
        from db.manager import get_all_chunks
        chunks = get_all_chunks()
        parts = [c["content"] for c in chunks if c["source_name"] == source_name]
        full = "\n\n".join(parts)
        return (full[:max_chars] + "\n\n...(kısaltıldı)") if len(full) > max_chars else full
    except Exception as e:
        return f"Önizleme yüklenemedi: {e}"


def _get_starter_questions() -> list:
    try:
        from db.manager import get_sources
        sources = get_sources()
        if not sources:
            return []
        questions = []
        for src in sources[:4]:
            name = re.sub(r"\.[^.]+$", "", src).replace("_", " ").replace("-", " ")
            display = f"📄 {name} hakkında bilgi ver"
            actual = f"{name} hakkında kapsamlı bilgi ver"
            questions.append((display, actual))
        return questions
    except Exception:
        return []


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            f'<div class="sb-brand">'
            f'<div class="sb-brand-title">{t("app_title")}</div>'
            f'<div class="sb-brand-sub">{t("app_subtitle")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        lang_idx = 0 if st.session_state.lang == "tr" else 1
        choice = st.radio(
            t("lang_label"), ["TR", "EN"],
            index=lang_idx, horizontal=True, label_visibility="collapsed", key="lang_radio",
        )
        new_lang = "tr" if choice == "TR" else "en"
        if new_lang != st.session_state.lang:
            st.session_state.lang = new_lang
            st.rerun()

        st.markdown(f'<div class="sb-section-label">{t("sys_status")}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="sb-status-pill"><span class="sb-dot"></span><span>{t("models_ready")}</span></div>',
            unsafe_allow_html=True,
        )

        st.markdown(f'<div class="sb-section-label">{t("model_label")}</div>', unsafe_allow_html=True)
        models_list = getattr(config, "AVAILABLE_LLM_MODELS", [
            ("qwen3-1.7b",   "Qwen3-1.7B (Hizli)"),
            ("qwen3-4b",     "Qwen3-4B (Dengeli)"),
            ("phi-3.5-mini", "Phi-3.5-mini (Yavas)"),
        ])
        model_aliases = [alias for alias, _ in models_list]
        model_labels  = [label for _, label in models_list]
        current_idx   = model_aliases.index(st.session_state.selected_model) \
                        if st.session_state.selected_model in model_aliases else 0

        sel_label = st.selectbox(
            t("model_label"), options=model_labels, index=current_idx,
            key="model_selector", label_visibility="collapsed",
        )
        chosen_alias = model_aliases[model_labels.index(sel_label)]
        if chosen_alias != st.session_state.selected_model:
            st.session_state.selected_model = chosen_alias
            pip = st.session_state.get("pipeline")
            if pip is not None:
                with st.spinner(t("model_switching")):
                    try:
                        pip.switch_llm_model(chosen_alias)
                        st.success(f"Model: {chosen_alias}")
                    except Exception as e:
                        st.error(f"Model degistirme hatasi: {e}")
            st.rerun()

        st.markdown(f'<div class="sb-section-label">{t("doc_upload")}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="font-size:0.7rem;color:#9CA3AF;margin-bottom:0.35rem;">{t("upload_hint")}</div>',
            unsafe_allow_html=True,
        )
        uploader_key = f"uploader_{st.session_state.uploader_key_idx}"
        uploaded = st.file_uploader(
            label=t("upload_btn"), type=["txt", "md", "pdf"],
            label_visibility="collapsed", key=uploader_key,
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
                expiry = time.time() + 3.0
                if res["ok"]:
                    msg = t("upload_ok", f=uploaded.name, n=res["chunks"])
                    st.session_state.upload_flash = [(True, msg, expiry)]
                else:
                    msg = t("upload_err", f=uploaded.name, e=res["error"])
                    st.session_state.upload_flash = [(False, msg, expiry)]
                st.session_state.uploader_key_idx += 1
                st.rerun()

        now = time.time()
        active_flash = [(ok, msg, exp) for (ok, msg, exp) in st.session_state.upload_flash if exp > now]
        st.session_state.upload_flash = active_flash
        for ok, msg, _ in active_flash:
            if ok: st.success(msg)
            else:  st.error(msg)

        st.markdown(f'<div class="sb-section-label">{t("indexed_docs")}</div>', unsafe_allow_html=True)
        try:
            from db.manager import get_sources, get_chunk_count, clear_source, get_all_chunks
            sources = get_sources()
            chunk_count = get_chunk_count()
            if sources:
                all_chunks_data = get_all_chunks()
                chunk_per_src = {}
                for c in all_chunks_data:
                    sn = c["source_name"]
                    chunk_per_src[sn] = chunk_per_src.get(sn, 0) + 1
                with st.container(height=220):
                    for src in sources:
                        icon = "📕" if src.endswith(".pdf") else "📄"
                        c_count = chunk_per_src.get(src, 0)
                        cols = st.columns([5, 1, 1])
                        with cols[0]:
                            st.markdown(
                                f'<div class="doc-row">'
                                f'<span class="doc-name" title="{html.escape(src)}">{icon} {html.escape(src)}</span>'
                                f'<span class="doc-chunks">{c_count} {t("chunks_label")}</span>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                        with cols[1]:
                            if st.button("...", key=f"prv_{src}", help=f"Onizle: {src}"):
                                st.session_state.preview_doc = src
                                st.rerun()
                        with cols[2]:
                            if st.button("x", key=f"del_{src}", help=f"Sil: {src}"):
                                clear_source(src)
                                if st.session_state.preview_doc == src:
                                    st.session_state.preview_doc = None
                                st.rerun()
                st.markdown(
                    f'<div class="doc-count-bar">{t("total_docs", n=len(sources), c=chunk_count)}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption(t("no_docs"))
        except Exception as e:
            st.caption(f"Hata: {e}")

        st.markdown('<div class="sb-footer">', unsafe_allow_html=True)
        st.markdown('<div class="sb-clear-btn">', unsafe_allow_html=True)
        if st.button("Sohbeti Temizle", key="clear_chat_btn", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pending_question = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sb-privacy">🔒 {t("privacy")}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def render_preview() -> None:
    doc = st.session_state.get("preview_doc")
    if not doc:
        return
    with st.expander(f"Belge Onizlemesi: {doc}", expanded=True):
        content = _preview_text(doc)
        st.text_area("preview_content", value=content, height=240, disabled=True, label_visibility="collapsed")
        if st.button(t("preview_close"), key="close_prev"):
            st.session_state.preview_doc = None
            st.rerun()


def _md_to_html(text: str) -> str:
    if not text:
        return ""
    safe = html.escape(text)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"\*(.+?)\*", r"<em>\1</em>", safe)
    safe = re.sub(
        r"`(.+?)`",
        r'<code style="background:#F3F4F6;padding:1px 5px;border-radius:4px;font-size:0.86em;font-family:monospace;">\1</code>',
        safe,
    )
    lines = safe.split("\n")
    output = []
    in_list = False
    list_type = "ul"
    for line in lines:
        s = line.strip()
        if not s:
            if in_list: output.append(f"</{list_type}>"); in_list = False
            output.append('<div style="height:0.3rem;"></div>')
            continue
        if s.startswith("### "):
            if in_list: output.append(f"</{list_type}>"); in_list = False
            output.append(f'<div style="font-weight:700;font-size:0.95rem;margin:0.5rem 0 0.2rem;color:#111827;">{s[4:]}</div>')
        elif s.startswith("## "):
            if in_list: output.append(f"</{list_type}>"); in_list = False
            output.append(f'<div style="font-weight:700;font-size:1rem;margin:0.6rem 0 0.2rem;color:#111827;">{s[3:]}</div>')
        elif s.startswith("# "):
            if in_list: output.append(f"</{list_type}>"); in_list = False
            output.append(f'<div style="font-weight:700;font-size:1.07rem;margin:0.65rem 0 0.25rem;color:#111827;">{s[2:]}</div>')
        elif s.startswith(("- ", "* ", "• ")):
            if not in_list or list_type != "ul":
                if in_list: output.append(f"</{list_type}>")
                output.append('<ul style="margin:0.3rem 0;padding-left:1.3rem;">')
                in_list = True; list_type = "ul"
            output.append(f'<li style="margin-bottom:0.18rem;line-height:1.65;">{s[2:].strip()}</li>')
        elif re.match(r"^\d+\.\s+", s):
            if not in_list or list_type != "ol":
                if in_list: output.append(f"</{list_type}>")
                output.append('<ol style="margin:0.3rem 0;padding-left:1.3rem;">')
                in_list = True; list_type = "ol"
            item = re.sub(r"^\d+\.\s+", "", s)
            output.append(f'<li style="margin-bottom:0.18rem;line-height:1.65;">{item}</li>')
        else:
            if in_list: output.append(f"</{list_type}>"); in_list = False
            output.append(f'<p style="margin:0.22rem 0;line-height:1.7;">{s}</p>')
    if in_list:
        output.append(f"</{list_type}>")
    return "".join(output)


def render_welcome() -> None:
    starter_qs = _get_starter_questions()
    st.markdown(
        f'<div class="welcome-wrap">'
        f'<div class="welcome-icon">📋</div>'
        f'<div class="welcome-title">{t("welcome_title")}</div>'
        f'<div class="welcome-subtitle">{t("welcome_subtitle")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if starter_qs:
        col1, col2 = st.columns(2)
        for idx, (display, actual) in enumerate(starter_qs):
            target = col1 if idx % 2 == 0 else col2
            with target:
                st.markdown('<div class="starter-wrapper">', unsafe_allow_html=True)
                if st.button(display, key=f"sq_{idx}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": actual})
                    st.session_state.pending_question = actual
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)


def render_messages() -> None:
    if not st.session_state.messages and not st.session_state.pending_question:
        render_welcome()
        return
    for msg in st.session_state.messages:
        role        = msg["role"]
        content     = msg["content"]
        sources     = msg.get("sources", [])
        latency     = msg.get("latency", "")
        chunks_used = msg.get("chunks_used", 0)
        if role == "user":
            safe = html.escape(content).replace("\n", "<br>")
            st.markdown(
                f'<div class="msg-user-wrap"><div class="msg-user-pill">{safe}</div></div>',
                unsafe_allow_html=True,
            )
        else:
            body_html = _md_to_html(content)
            src_html = ""
            if sources:
                chips = "".join(
                    f'<span class="src-chip">📄 {html.escape(s)}</span>' for s in sources
                )
                src_html = (
                    f'<div class="src-section">'
                    f'<span class="src-section-label">{t("src_label")}</span>'
                    f'<div class="src-chips">{chips}</div>'
                    f'</div>'
                )
            meta_parts = []
            if latency:
                meta_parts.append(f'<span class="msg-meta-item">⏱ {html.escape(latency)}</span>')
            if chunks_used:
                meta_parts.append(f'<span class="msg-meta-item">📦 {chunks_used} parça</span>')
            meta_html = (
                f'<div class="msg-meta-row">{"<span class=\"msg-meta-sep\">·</span>".join(meta_parts)}</div>'
                if meta_parts else ""
            )
            st.markdown(
                f'<div class="msg-bot-wrap">'
                f'<div class="msg-bot-header">'
                f'<div class="msg-bot-icon">AI</div>'
                f'<span class="msg-bot-label">{t("ai_label")}</span>'
                f'</div>'
                f'<div class="msg-bot-card">'
                f'<div class="msg-bot-body">{body_html}</div>'
                f'{src_html}'
                f'{meta_html}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def main():
    _init()
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
    render_messages()

    if st.session_state.pending_question:
        question = st.session_state.pending_question
        with st.spinner(t("searching")):
            try:
                pip = st.session_state.pipeline
                response = pip.ask(question, chat_history=st.session_state.messages[:-1])
                lat = f"{response.latency_sec:.1f}s"
                if response.has_error:
                    bot_content = f"Hata: {response.error}"
                    sources = []; chunks_used = 0
                else:
                    bot_content = response.answer
                    sources = response.unique_sources
                    chunks_used = response.chunks_used
            except Exception as e:
                bot_content = f"Hata: {e}"
                sources = []; chunks_used = 0; lat = ""

        st.session_state.messages.append({
            "role": "assistant", "content": bot_content,
            "sources": sources, "latency": lat, "chunks_used": chunks_used,
        })
        st.session_state.pending_question = None
        st.rerun()

    prompt = st.chat_input(placeholder=t("placeholder"), disabled=not pipeline_ready)
    if prompt and prompt.strip():
        question = prompt.strip()
        st.session_state.messages.append({"role": "user", "content": question})
        st.session_state.pending_question = question
        st.rerun()


if __name__ == "__main__":
    main()
