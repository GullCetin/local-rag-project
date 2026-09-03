"""
ui/app.py - Local RAG Asistani (Modern Cortex-Inspired Enterprise UI)
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
    page_icon="✨",
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
        "searching":        "Yanıt hazırlanıyor...",
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
        "searching":        "Preparing answer...",
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
# Modern Cortex-Inspired CSS (Minimalist, Clean, Enterprise AI)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Base Typography & Color Reset */
html, body, .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    background-color: #FAFAFC !important;
    color: #111827 !important;
    font-size: 14.5px !important;
    line-height: 1.6 !important;
    letter-spacing: -0.01em !important;
    -webkit-font-smoothing: antialiased !important;
}

/* CRITICAL: Protect Material Symbols & icons from font override (fixes 'uploadupload' & overlapping icon text bugs) */
[data-testid="stIconMaterial"],
.material-symbols-rounded,
.material-icons,
[class*="material-symbols"] {
    font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
    font-weight: normal !important;
    font-style: normal !important;
    line-height: 1 !important;
    text-transform: none !important;
    letter-spacing: normal !important;
    word-wrap: normal !important;
    white-space: nowrap !important;
    direction: ltr !important;
}

/* Header cleanup */
header[data-testid="stHeader"] {
    background-color: rgba(250, 250, 252, 0.85) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05) !important;
}
#MainMenu, footer, [data-testid="stDecoration"], [data-testid="stToolbar"] {
    display: none !important;
}

/* Sidebar Open/Close Controls */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
}
[data-testid="stExpandSidebarButton"] button,
[data-testid="stSidebarCollapsedControl"] button {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: #FFFFFF !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 9px !important;
    color: #4B5563 !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
    width: 36px !important;
    height: 36px !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
}
[data-testid="stExpandSidebarButton"] button:hover,
[data-testid="stSidebarCollapsedControl"] button:hover {
    color: #7C3AED !important;
    border-color: #DDD6FE !important;
    box-shadow: 0 4px 12px rgba(124, 58, 237, 0.15) !important;
}
[data-testid="stSidebarCollapseButton"] {
    display: block !important;
    visibility: visible !important;
}
[data-testid="stSidebarCollapseButton"] button {
    color: #9CA3AF !important;
    border-radius: 6px !important;
}
[data-testid="stSidebarCollapseButton"] button:hover {
    color: #111827 !important;
    background: #F3F4F6 !important;
}

/* Sidebar Layout */
[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #E5E7EB !important;
    box-shadow: 2px 0 16px rgba(0, 0, 0, 0.02) !important;
}
[data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"] {
    padding: 1.1rem 0.95rem !important;
    background-color: #FFFFFF !important;
}

/* Sidebar Brand Header */
.sb-brand {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #F3F4F6;
    margin-bottom: 0.45rem;
}
.sb-brand-icon {
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%);
    color: #FFFFFF;
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 8px rgba(124, 58, 237, 0.22);
    flex-shrink: 0;
}
.sb-brand-text {
    display: flex;
    flex-direction: column;
    min-width: 0;
}
.sb-brand-title {
    font-size: 0.96rem;
    font-weight: 700;
    color: #111827;
    letter-spacing: -0.025em;
    line-height: 1.2;
}
.sb-brand-sub {
    font-size: 0.69rem;
    color: #9CA3AF;
    font-weight: 500;
    line-height: 1.2;
    margin-top: 0.15rem;
}

/* Sidebar Section Titles */
.sb-section-label {
    font-size: 0.67rem;
    font-weight: 600;
    color: #9CA3AF;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 0.65rem 0 0.3rem 0;
}

/* Segmented Control (TR/EN) */
[data-testid="stSidebar"] [data-testid="stSegmentedControl"] {
    margin-bottom: 0.4rem !important;
}
[data-testid="stSidebar"] [data-testid="stSegmentedControl"] > div {
    background-color: #F3F4F6 !important;
    border-radius: 8px !important;
    padding: 2px !important;
    border: 1px solid #E5E7EB !important;
}
[data-testid="stSidebar"] [data-testid="stSegmentedControl"] button {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 0.2rem 0.6rem !important;
    border-radius: 6px !important;
    border: none !important;
    color: #6B7280 !important;
    transition: all 0.15s ease !important;
}
[data-testid="stSidebar"] [data-testid="stSegmentedControl"] button[aria-selected="true"] {
    background: #FFFFFF !important;
    color: #7C3AED !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
}

/* Status Pill */
.sb-status-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    background: #F9FAFB;
    border: 1px solid #E5E7EB;
    border-radius: 99px;
    padding: 0.22rem 0.65rem;
    font-size: 0.73rem;
    font-weight: 500;
    color: #374151;
    margin-bottom: 0.4rem;
}
.sb-dot {
    width: 6px;
    height: 6px;
    background: #10B981;
    border-radius: 50%;
    box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
    flex-shrink: 0;
}

/* Model Selector */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
    background: #FAFAFC !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 8px !important;
    font-size: 0.81rem !important;
    color: #111827 !important;
    min-height: 34px !important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div:hover {
    border-color: #D1D5DB !important;
}

/* Compact Modern File Uploader Dropzone */
[data-testid="stFileUploader"] {
    background: #FAFAFC !important;
    border: 1.5px dashed #D1D5DB !important;
    border-radius: 10px !important;
    padding: 0.4rem 0.5rem !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #8B5CF6 !important;
    background: #FAF8FF !important;
}
[data-testid="stFileUploader"] section {
    border: none !important;
    background: transparent !important;
    padding: 0.3rem 0.1rem !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] {
    display: none !important;
}
[data-testid="stFileUploader"] button {
    background: #FFFFFF !important;
    color: #374151 !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 7px !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    padding: 0.28rem 0.7rem !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    transition: all 0.15s ease !important;
}
[data-testid="stFileUploader"] button:hover {
    background: #F9FAFB !important;
    border-color: #D1D5DB !important;
    color: #111827 !important;
}

/* Document List Items */
.doc-item-info {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    min-width: 0;
    padding: 0.22rem 0;
}
.doc-svg-icon {
    color: #7C3AED;
    flex-shrink: 0;
}
.doc-text-block {
    display: flex;
    flex-direction: column;
    min-width: 0;
    overflow: hidden;
}
.doc-filename {
    font-size: 0.78rem;
    font-weight: 500;
    color: #1F2937;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.25;
}
.doc-badge {
    font-size: 0.67rem;
    color: #9CA3AF;
    font-weight: 400;
    line-height: 1.2;
}
.doc-count-bar {
    font-size: 0.72rem;
    color: #6B7280;
    padding-top: 0.4rem;
    border-top: 1px solid #F3F4F6;
    margin-top: 0.2rem;
}

/* Action Icon Buttons in Document List */
[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] button {
    background: transparent !important;
    border: 1px solid transparent !important;
    box-shadow: none !important;
    padding: 0.15rem !important;
    min-height: 28px !important;
    height: 28px !important;
    width: 28px !important;
    border-radius: 6px !important;
    color: #9CA3AF !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: all 0.15s ease !important;
}
[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] button:hover {
    background: #F3F4F6 !important;
    color: #111827 !important;
    border-color: #E5E7EB !important;
}
[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] button:last-child:hover {
    background: #FEF2F2 !important;
    color: #EF4444 !important;
    border-color: #FECACA !important;
}

/* Sidebar Footer & Clear Button */
.sb-footer {
    border-top: 1px solid #F3F4F6;
    padding-top: 0.6rem;
    margin-top: auto;
}
div.sb-clear-btn button {
    background: #FFFFFF !important;
    color: #6B7280 !important;
    border: 1px solid #E5E7EB !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    padding: 0.4rem 0.5rem !important;
    border-radius: 8px !important;
    width: 100% !important;
    transition: all 0.15s ease !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
}
div.sb-clear-btn button:hover {
    background: #FEF2F2 !important;
    color: #DC2626 !important;
    border-color: #FECACA !important;
}
.sb-privacy {
    font-size: 0.68rem;
    color: #9CA3AF;
    text-align: center;
    margin-top: 0.45rem;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.3rem;
}

/* Fade animation for upload alerts */
[data-testid="stSidebar"] [data-testid="stAlert"] {
    animation: sbFade 0.4s ease 2.5s forwards;
    border-radius: 8px !important;
    border: none !important;
    font-size: 0.78rem !important;
}
@keyframes sbFade {
    to { opacity: 0; max-height: 0; margin: 0; padding: 0; overflow: hidden; }
}

/* Cortex Welcome Screen (Orb + Clean Hero + Sleek Chips) */
.cortex-hero-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 2.2rem 1rem 1rem 1rem;
    max-width: 680px;
    margin: 0 auto;
}
.cortex-orb-container {
    position: relative;
    width: 68px;
    height: 68px;
    margin-bottom: 1.2rem;
}
.cortex-orb {
    width: 68px;
    height: 68px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 30%, #E9D5FF 0%, #A855F7 50%, #7C3AED 90%);
    box-shadow: 0 0 38px 8px rgba(168, 85, 247, 0.35), inset 0 2px 4px rgba(255,255,255,0.7);
    filter: blur(0.5px);
    animation: orbFloat 4s ease-in-out infinite alternate;
}
@keyframes orbFloat {
    0% { transform: translateY(0px) scale(1); }
    100% { transform: translateY(-4px) scale(1.03); }
}
.welcome-brand-text {
    font-size: 1.15rem;
    font-weight: 600;
    color: #7C3AED;
    letter-spacing: -0.02em;
    margin-bottom: 0.2rem;
}
.welcome-title {
    font-size: 1.85rem;
    font-weight: 700;
    color: #111827;
    letter-spacing: -0.03em;
    margin-bottom: 0.45rem;
    line-height: 1.25;
}
.welcome-subtitle {
    font-size: 0.9rem;
    color: #6B7280;
    line-height: 1.5;
    margin-bottom: 1.8rem;
    max-width: 520px;
}

/* Suggestion / Quick Question Cards */
div.starter-wrapper button {
    background: #FFFFFF !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 12px !important;
    padding: 0.75rem 0.95rem !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    color: #374151 !important;
    text-align: left !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
    transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
    min-height: 52px !important;
    line-height: 1.4 !important;
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
}
div.starter-wrapper button:hover {
    border-color: #8B5CF6 !important;
    background: #FAF8FF !important;
    box-shadow: 0 4px 14px rgba(124, 58, 237, 0.08) !important;
    color: #6D28D9 !important;
    transform: translateY(-1px);
}

/* Chat Messages */
.msg-user-wrap {
    display: flex;
    justify-content: flex-end;
    margin: 1rem 0 0.35rem 0;
}
.msg-user-pill {
    background: #F3EEFF;
    border: 1px solid #DDD6FE;
    color: #1E1B4B;
    font-size: 0.92rem;
    font-weight: 500;
    padding: 0.55rem 0.95rem;
    border-radius: 16px 16px 4px 16px;
    max-width: 72%;
    word-break: break-word;
    line-height: 1.55;
    box-shadow: 0 1px 3px rgba(124, 58, 237, 0.04);
}

.msg-bot-wrap {
    margin: 0.35rem 0 1.2rem 0;
}
.msg-bot-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.45rem;
}
.msg-bot-icon {
    width: 22px;
    height: 22px;
    background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%);
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 2px 6px rgba(124, 58, 237, 0.2);
}
.msg-bot-icon svg {
    color: #FFFFFF;
}
.msg-bot-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: #374151;
}
.msg-bot-card {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 14px;
    padding: 1.05rem 1.25rem;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03);
}
.msg-bot-body {
    font-size: 0.92rem;
    color: #111827;
    line-height: 1.68;
}
.src-section {
    margin-top: 0.85rem;
    padding-top: 0.75rem;
    border-top: 1px solid #F3F4F6;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}
.src-section-label {
    font-size: 0.68rem;
    font-weight: 600;
    color: #9CA3AF;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    flex-shrink: 0;
}
.src-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
}
.src-chip {
    background: #F9FAFB;
    border: 1px solid #E5E7EB;
    color: #374151;
    padding: 0.2rem 0.55rem;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
}
.src-chip svg {
    color: #7C3AED;
}
.msg-meta-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.55rem;
}
.msg-meta-item {
    font-size: 0.69rem;
    color: #9CA3AF;
    font-weight: 400;
}
.msg-meta-sep {
    color: #E5E7EB;
}

/* Floating Chat Input Composer */
[data-testid="stBottom"] {
    background: linear-gradient(180deg, rgba(250, 250, 252, 0) 0%, rgba(250, 250, 252, 0.95) 25%, #FAFAFC 100%) !important;
    border-top: none !important;
    padding-bottom: 0.5rem !important;
}
[data-testid="stBottom"] > div {
    background: transparent !important;
}
[data-testid="stChatInput"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 20px !important;
    box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.06) !important;
    max-width: 780px !important;
    margin: 0 auto 0.5rem auto !important;
    transition: all 0.2s ease !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: #7C3AED !important;
    box-shadow: 0 4px 24px -2px rgba(124, 58, 237, 0.12), 0 0 0 1px #7C3AED !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: #111827 !important;
    font-size: 0.92rem !important;
    padding: 0.65rem 1rem !important;
    line-height: 1.5 !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #9CA3AF !important;
}
[data-testid="stChatInput"] button {
    background: #7C3AED !important;
    color: #FFFFFF !important;
    border-radius: 12px !important;
    border: none !important;
    width: 32px !important;
    height: 32px !important;
    margin-right: 0.4rem !important;
    transition: all 0.15s ease !important;
}
[data-testid="stChatInput"] button:hover {
    background: #6D28D9 !important;
}

/* Modal Dialog Styling (Belge Önizlemesi) */
div[data-testid="stDialog"] div[role="dialog"] {
    border-radius: 16px !important;
    border: 1px solid #E5E7EB !important;
    box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.14) !important;
    background: #FFFFFF !important;
    padding: 1.5rem !important;
}
.modal-file-bar {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    background: #F3EEFF;
    border: 1px solid #DDD6FE;
    color: #6D28D9;
    border-radius: 8px;
    padding: 0.35rem 0.75rem;
    font-size: 0.82rem;
    font-weight: 600;
    margin-bottom: 0.85rem;
}

/* Minimalist Modern Loading Indicator */
[data-testid="stSpinner"] {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 0.6rem !important;
    padding: 0.75rem 1rem !important;
    background: #FFFFFF !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 12px !important;
    max-width: 260px !important;
    margin: 0.5rem 0 !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03) !important;
    font-size: 0.83rem !important;
    color: #4B5563 !important;
    font-weight: 500 !important;
}
[data-testid="stSpinner"] > div {
    border-top-color: #7C3AED !important;
}
</style>
""", unsafe_allow_html=True)

# Ensure sidebar is opened if collapsed
st.html("""
<script>
(function() {
    function autoExpandSidebar() {
        try {
            const win = window.parent || window;
            const doc = win.document || document;
            try {
                Object.keys(win.localStorage).forEach(k => {
                    if (k.indexOf('SidebarCollapsed') !== -1) {
                        win.localStorage.setItem(k, 'false');
                    }
                });
            } catch(e) {}

            const sidebar = doc.querySelector('[data-testid="stSidebar"]');
            const expandBtn = doc.querySelector('[data-testid="stExpandSidebarButton"] button, [data-testid="stSidebarCollapsedControl"] button, button[aria-label="Expand sidebar"]');
            if (sidebar && sidebar.getAttribute('aria-expanded') === 'false' && expandBtn) {
                expandBtn.click();
            }
        } catch(e) {}
    }
    autoExpandSidebar();
    setTimeout(autoExpandSidebar, 150);
    setTimeout(autoExpandSidebar, 500);
    setTimeout(autoExpandSidebar, 1200);
})();
</script>
""", unsafe_allow_javascript=True)


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
        "sidebar_open":       True,
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


def _preview_text(source_name: str, max_chars: int = 5000) -> str:
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
        lang = st.session_state.get("lang", "tr")
        if lang == "tr":
            starters = [
                ("Ana sayfada hangi componentler kullanılmaktadır?", "mobil uygulamamızda ana sayfada hangi component kullanılmaktadır"),
                ("`429 Too Many Requests` hatası ne anlama gelir?", "mobil uygulamada `429 Too Many Requests` hatası ne anlama gelmektedir"),
                ("Güvenlik politikasının ana hatları nelerdir?", "uygulamamızın güvenlik politikası ana hatları nelerdir"),
                ("Oturum süresi ne kadar olarak belirlenmiştir?", "uygulamada oturum süresi ne olarak belirlenmiştir"),
            ]
        else:
            starters = [
                ("What components are used on the main page?", "which component is used on the main page of our mobile app"),
                ("What does the `429 Too Many Requests` error mean?", "what does the `429 Too Many Requests` error mean in our mobile app"),
                ("What are the main points of the security policy?", "what are the main points of our app's security policy"),
                ("What is the session duration set to?", "what is the session duration set to in our app"),
            ]
        return starters
    except Exception:
        return []


def render_sidebar() -> None:
    with st.sidebar:
        # Brand Header
        st.markdown(
            f'''<div class="sb-brand">
                <div class="sb-brand-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
                    </svg>
                </div>
                <div class="sb-brand-text">
                    <div class="sb-brand-title">{t("app_title")}</div>
                    <div class="sb-brand-sub">{t("app_subtitle")}</div>
                </div>
            </div>''',
            unsafe_allow_html=True,
        )

        # Language Switcher (Segmented Control)
        curr_lang = "TR" if st.session_state.lang == "tr" else "EN"
        choice = st.segmented_control(
            label=t("lang_label"),
            options=["TR", "EN"],
            selection_mode="single",
            default=curr_lang,
            label_visibility="collapsed",
            key="lang_segmented",
        )
        if choice and choice != curr_lang:
            st.session_state.lang = "tr" if choice == "TR" else "en"
            st.rerun()

        # Status Pill
        st.markdown(
            f'<div class="sb-status-pill"><span class="sb-dot"></span><span>{t("models_ready")}</span></div>',
            unsafe_allow_html=True,
        )

        # Model Selector
        st.markdown(f'<div class="sb-section-label">{t("model_label")}</div>', unsafe_allow_html=True)
        models_list = getattr(config, "AVAILABLE_LLM_MODELS", [
            ("qwen3-1.7b",   "Qwen3-1.7B (Hızlı)"),
            ("qwen3-4b",     "Qwen3-4B (Dengeli)"),
            ("phi-3.5-mini", "Phi-3.5-mini (Yavaş)"),
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
                        st.error(f"Model değiştirme hatası: {e}")
            st.rerun()

        # Document Upload
        st.markdown(f'<div class="sb-section-label">{t("doc_upload")}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="font-size:0.69rem;color:#9CA3AF;margin-bottom:0.3rem;">{t("upload_hint")}</div>',
            unsafe_allow_html=True,
        )
        uploader_key = f"uploader_{st.session_state.uploader_key_idx}"
        uploaded = st.file_uploader(
            label="", type=["txt", "md", "pdf"],
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

        # Indexed Documents List
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
                with st.container(height=200):
                    for src in sources:
                        c_count = chunk_per_src.get(src, 0)
                        cols = st.columns([5.6, 1.2, 1.2], vertical_alignment="center")
                        with cols[0]:
                            st.markdown(
                                f'''<div class="doc-item-info">
                                    <svg class="doc-svg-icon" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                        <polyline points="14 2 14 8 20 8"></polyline>
                                        <line x1="16" y1="13" x2="8" y2="13"></line>
                                        <line x1="16" y1="17" x2="8" y2="17"></line>
                                        <polyline points="10 9 9 9 8 9"></polyline>
                                    </svg>
                                    <div class="doc-text-block">
                                        <span class="doc-filename" title="{html.escape(src)}">{html.escape(src)}</span>
                                        <span class="doc-badge">{c_count} {t("chunks_label")}</span>
                                    </div>
                                </div>''',
                                unsafe_allow_html=True,
                            )
                        with cols[1]:
                            if st.button("", icon=":material/visibility:", key=f"prv_{src}", help=f"{t('prv_btn')}: {src}"):
                                st.session_state.preview_doc = src
                                st.rerun()
                        with cols[2]:
                            if st.button("", icon=":material/delete:", key=f"del_{src}", help=f"{t('del_btn')}: {src}"):
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

        # Sidebar Footer
        st.markdown('<div class="sb-footer">', unsafe_allow_html=True)
        st.markdown('<div class="sb-clear-btn">', unsafe_allow_html=True)
        if st.button(t("clear_chat"), key="clear_chat_btn", icon=":material/refresh:", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pending_question = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(
            f'''<div class="sb-privacy">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
                <span>{t("privacy")}</span>
            </div>''',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Modal Dialog: Belge Önizlemesi (Full-Screen Overlay Modal)
# ---------------------------------------------------------------------------
def _on_preview_dismiss() -> None:
    st.session_state.preview_doc = None


@st.dialog("Belge Önizlemesi", width="large", on_dismiss=_on_preview_dismiss)
def show_preview_dialog(doc_name: str) -> None:
    content = _preview_text(doc_name, max_chars=6000)
    st.markdown(
        f'''<div class="modal-file-bar">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            <span>{html.escape(doc_name)}</span>
        </div>''',
        unsafe_allow_html=True,
    )
    st.text_area(
        label="preview_content",
        value=content,
        height=420,
        disabled=True,
        label_visibility="collapsed",
    )
    col_spacer, col_btn = st.columns([5, 1.2])
    with col_btn:
        if st.button(t("preview_close"), key="close_dialog_btn", type="primary", use_container_width=True):
            st.session_state.preview_doc = None
            st.rerun()


def render_preview() -> None:
    doc = st.session_state.get("preview_doc")
    if doc:
        show_preview_dialog(doc)


# ---------------------------------------------------------------------------
# Message Rendering Helpers
# ---------------------------------------------------------------------------
def _md_to_html(text: str) -> str:
    if not text:
        return ""
    safe = html.escape(text)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"\*(.+?)\*", r"<em>\1</em>", safe)
    safe = re.sub(
        r"`(.+?)`",
        r'<code style="background:#F3F4F6;color:#4C1D95;padding:1px 5px;border-radius:4px;font-size:0.86em;font-family:monospace;">\1</code>',
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
        f'''<div class="cortex-hero-wrap">
            <div class="cortex-orb-container">
                <div class="cortex-orb"></div>
            </div>
            <div class="welcome-brand-text">{t("app_title")}</div>
            <div class="welcome-title">{t("welcome_title")}</div>
            <div class="welcome-subtitle">{t("welcome_subtitle")}</div>
        </div>''',
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
                    f'''<span class="src-chip">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                        {html.escape(s)}
                    </span>''' for s in sources
                )
                src_html = (
                    f'<div class="src-section">'
                    f'<span class="src-section-label">{t("src_label")}</span>'
                    f'<div class="src-chips">{chips}</div>'
                    f'</div>'
                )
            st.markdown(
                f'''<div class="msg-bot-wrap">
                    <div class="msg-bot-header">
                        <div class="msg-bot-icon">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
                            </svg>
                        </div>
                        <span class="msg-bot-label">{t("ai_label")}</span>
                    </div>
                    <div class="msg-bot-card">
                        <div class="msg-bot-body">{body_html}</div>
                        {src_html}
                    </div>
                </div>''',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Ana Uygulama Döngüsü
# ---------------------------------------------------------------------------
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

    # Dynamic Sidebar Visibility Control
    sidebar_visible = st.session_state.get("sidebar_open", True)
    if sidebar_visible:
        st.markdown("""
        <style>
        section[data-testid="stSidebar"] {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            min-width: 310px !important;
            max-width: 310px !important;
            width: 310px !important;
            transform: none !important;
            margin-left: 0 !important;
        }
        [data-testid="stSidebarContent"],
        [data-testid="stSidebarUserContent"] {
            display: flex !important;
            flex-direction: column !important;
            visibility: visible !important;
            opacity: 1 !important;
        }
        </style>
        """, unsafe_allow_html=True)
        render_sidebar()
    else:
        st.markdown("""
        <style>
        section[data-testid="stSidebar"] {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            margin-left: -350px !important;
        }
        </style>
        """, unsafe_allow_html=True)

    if not sidebar_visible:
        top_cols = st.columns([1, 20])
        with top_cols[0]:
            if st.button("", icon=":material/dock_to_left:", key="open_sidebar_btn", help="Menüyü Göster"):
                st.session_state.sidebar_open = True
                st.rerun()

    if not pipeline_ready:
        st.error(f"{t('err_loading')}: {st.session_state.error_message}")
        st.info(t("err_check"))
        return

    # Trigger full-screen modal when preview is active
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
