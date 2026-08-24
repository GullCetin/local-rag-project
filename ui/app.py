"""
ui/app.py — Streamlit Web Arayüzü
===================================
Local RAG AI Assistant için profesyonel, modern Streamlit arayüzü.

Çalıştır:
  streamlit run ui/app.py

Özellikler:
  - Chat tabanlı sohbet arayüzü
  - Kaynak doküman kartları
  - Yükleme animasyonu
  - Hata durumu yönetimi
  - Sidebar'da sistem durumu ve belgeler
  - Mesaj geçmişi (oturum boyunca)
"""

import os
import sys
import time
import logging

# Proje kökünü path'e ekle (streamlit farklı dizinden çalıştırabilir)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

from config import APP_TITLE, APP_DESCRIPTION

# Sayfa yapılandırması — st.set_page_config ilk Streamlit çağrısı olmalı
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS Stilleri
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* Import font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Hide Streamlit default header/footer/menu */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="stToolbar"] {display: none;}
[data-testid="stDecoration"] {display: none;}


/* Ana arka plan */
.stApp {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
    min-height: 100vh;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.04);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

/* Ana başlık */
.app-header {
    text-align: center;
    padding: 2rem 0 1rem 0;
}
.app-header h1 {
    font-size: 2.4rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.3rem;
}
.app-header p {
    color: rgba(255,255,255,0.5);
    font-size: 0.95rem;
    font-weight: 300;
}

/* Kullanıcı mesajı */
.user-message {
    display: flex;
    justify-content: flex-end;
    margin: 1rem 0 0.5rem 0;
}
.user-bubble {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    padding: 0.85rem 1.2rem;
    border-radius: 18px 18px 4px 18px;
    max-width: 72%;
    font-size: 0.95rem;
    line-height: 1.5;
    box-shadow: 0 4px 20px rgba(102, 126, 234, 0.35);
}

/* Bot mesajı */
.bot-message {
    display: flex;
    justify-content: flex-start;
    align-items: flex-start;
    margin: 0.5rem 0 1rem 0;
    gap: 0.75rem;
}
.bot-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: linear-gradient(135deg, #f093fb, #f5576c);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    flex-shrink: 0;
    box-shadow: 0 4px 15px rgba(240, 147, 251, 0.4);
}
.bot-bubble {
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.92);
    padding: 0.85rem 1.2rem;
    border-radius: 4px 18px 18px 18px;
    max-width: 75%;
    font-size: 0.95rem;
    line-height: 1.6;
    backdrop-filter: blur(10px);
}

/* Kaynak kartları */
.sources-section {
    margin-top: 0.6rem;
    padding-left: 48px;
}
.sources-label {
    color: rgba(255,255,255,0.4);
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
}
.source-tag {
    display: inline-block;
    background: rgba(102, 126, 234, 0.15);
    border: 1px solid rgba(102, 126, 234, 0.3);
    color: #a5b4fc;
    padding: 0.2rem 0.65rem;
    border-radius: 100px;
    font-size: 0.78rem;
    margin: 0.15rem 0.2rem;
    font-weight: 500;
}

/* Divider */
.chat-divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.06);
    margin: 0.5rem 0;
}

/* Sidebar bölüm başlıkları */
.sidebar-section-title {
    color: rgba(255,255,255,0.35);
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 1.2rem 0 0.5rem 0;
}

/* Durum badge'leri */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.7rem;
    border-radius: 100px;
    font-size: 0.8rem;
    font-weight: 500;
    margin: 0.2rem 0;
}
.status-ready {
    background: rgba(52, 211, 153, 0.15);
    border: 1px solid rgba(52, 211, 153, 0.3);
    color: #34d399;
}
.status-loading {
    background: rgba(251, 191, 36, 0.15);
    border: 1px solid rgba(251, 191, 36, 0.3);
    color: #fbbf24;
}
.status-error {
    background: rgba(248, 113, 113, 0.15);
    border: 1px solid rgba(248, 113, 113, 0.3);
    color: #f87171;
}

/* Hoşgeldin kartı */
.welcome-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
    margin: 2rem auto;
    max-width: 600px;
}
.welcome-card .icon {
    font-size: 3.5rem;
    margin-bottom: 1rem;
}
.welcome-card h3 {
    color: rgba(255,255,255,0.85);
    margin-bottom: 0.5rem;
    font-size: 1.2rem;
}
.welcome-card p {
    color: rgba(255,255,255,0.45);
    font-size: 0.9rem;
    line-height: 1.6;
}

/* Input alanı özelleştirme */
.stTextInput input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 12px !important;
    color: white !important;
    padding: 0.75rem 1rem !important;
    font-size: 0.95rem !important;
}
.stTextInput input:focus {
    border-color: rgba(102, 126, 234, 0.6) !important;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15) !important;
}

/* Gönder butonu */
.stButton button {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.6rem 1.5rem !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
}
.stButton button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5) !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.25); }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session State Başlatma
# ---------------------------------------------------------------------------
def init_session_state() -> None:
    """Streamlit session state değişkenlerini ilk çalıştırmada başlat."""
    if "pipeline" not in st.session_state:
        st.session_state.pipeline = None
    if "pipeline_status" not in st.session_state:
        st.session_state.pipeline_status = "not_started"  # not_started | loading | ready | error
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "error_message" not in st.session_state:
        st.session_state.error_message = None


# ---------------------------------------------------------------------------
# Pipeline Yükleme
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_pipeline():
    """
    RAG pipeline'ını yükler ve önbelleğe alır.
    
    @cache_resource sayesinde Streamlit her etkileşimde
    pipeline'ı yeniden yüklemez — bu kritik bir optimizasyon.
    Model yükleme 1-3 dakika sürebilir.
    """
    from rag.pipeline import RAGPipeline
    pipeline = RAGPipeline()
    pipeline.load()
    return pipeline


# ---------------------------------------------------------------------------
# UI Bileşenleri
# ---------------------------------------------------------------------------
def render_header() -> None:
    """Uygulama başlığını göster."""
    st.markdown("""
    <div class="app-header">
        <h1>🧠 Local RAG AI Assistant</h1>
        <p>Ask questions about your documents — 100% offline, powered by Microsoft Foundry Local</p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar(pipeline_ready: bool) -> None:
    """Sol panel: sistem durumu, yüklü belgeler, nasıl kullanılır."""
    with st.sidebar:
        st.markdown("### ⚡ Local RAG")
        
        # Sistem durumu
        st.markdown('<div class="sidebar-section-title">System Status</div>', unsafe_allow_html=True)
        
        status = st.session_state.pipeline_status
        if status == "ready":
            st.markdown('<div class="status-badge status-ready">🟢 Pipeline Ready</div>', unsafe_allow_html=True)
        elif status == "loading":
            st.markdown('<div class="status-badge status-loading">🟡 Loading Models...</div>', unsafe_allow_html=True)
        elif status == "error":
            st.markdown('<div class="status-badge status-error">🔴 Error</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-badge status-loading">⚪ Not Started</div>', unsafe_allow_html=True)

        # Yüklü belgeler
        st.markdown('<div class="sidebar-section-title">Loaded Documents</div>', unsafe_allow_html=True)
        try:
            from db.manager import get_sources, get_chunk_count
            sources = get_sources()
            chunk_count = get_chunk_count()
            
            if sources:
                for src in sources:
                    st.markdown(f"📄 `{src}`")
                st.caption(f"Total: {chunk_count} chunks indexed")
            else:
                st.caption("No documents loaded yet.")
                st.info("Run `python ingest.py` to load documents.")
        except Exception:
            st.caption("Database not initialized.")

        # Konuşma geçmişini temizle
        st.markdown('<div class="sidebar-section-title">Actions</div>', unsafe_allow_html=True)
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        # Nasıl kullanılır
        st.markdown('<div class="sidebar-section-title">How It Works</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="color: rgba(255,255,255,0.5); font-size: 0.8rem; line-height: 1.6;">
        1. 🔍 Your question is converted to a vector<br>
        2. 📚 Relevant document chunks are retrieved<br>
        3. 🧠 Local LLM generates a grounded answer<br>
        4. 📌 Sources are displayed with the response
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.caption("🔒 100% Offline • No data leaves your device")


def render_message(role: str, content: str, sources: list[str] = None) -> None:
    """Tek bir sohbet mesajını göster."""
    if role == "user":
        st.markdown(f"""
        <div class="user-message">
            <div class="user-bubble">{content}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Bot mesajı — içeriği Markdown olarak render et
        st.markdown(f"""
        <div class="bot-message">
            <div class="bot-avatar">🤖</div>
            <div class="bot-bubble">{content}</div>
        </div>
        """, unsafe_allow_html=True)

        # Kaynaklar
        if sources:
            source_tags = "".join(
                f'<span class="source-tag">📄 {src}</span>' for src in sources
            )
            st.markdown(f"""
            <div class="sources-section">
                <div class="sources-label">Sources</div>
                {source_tags}
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<hr class="chat-divider">', unsafe_allow_html=True)


def render_welcome() -> None:
    """Henüz sohbet başlamadıysa hoşgeldin kartını göster."""
    st.markdown("""
    <div class="welcome-card">
        <div class="icon">💬</div>
        <h3>Start a conversation</h3>
        <p>
            Ask any question about your documents.<br>
            The assistant will find relevant information and generate<br>
            an accurate, source-grounded answer — completely offline.
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_chat_history() -> None:
    """Tüm mesaj geçmişini göster."""
    for msg in st.session_state.messages:
        render_message(
            role=msg["role"],
            content=msg["content"],
            sources=msg.get("sources"),
        )


def render_input_area(pipeline_ready: bool) -> None:
    """Alt kısımdaki soru giriş alanını göster."""
    st.markdown("---")
    col1, col2 = st.columns([6, 1])

    with col1:
        question = st.text_input(
            label="question_input",
            placeholder="Ask a question about your documents..." if pipeline_ready else "⏳ Models are loading, please wait...",
            label_visibility="collapsed",
            disabled=not pipeline_ready,
            key="question_input",
        )
    with col2:
        send_clicked = st.button(
            "Send ➤",
            disabled=not pipeline_ready,
            use_container_width=True,
        )

    return question, send_clicked


# ---------------------------------------------------------------------------
# Ana Uygulama
# ---------------------------------------------------------------------------
def main():
    init_session_state()

    # Başlık
    render_header()

    # Pipeline'ı önbellekten al / ilk açılışta yükle
    try:
        with st.spinner("⏳ Modeller hafızaya alınıyor..."):
            pipeline = load_pipeline()
            st.session_state.pipeline = pipeline
            st.session_state.pipeline_status = "ready"
            st.session_state.error_message = None
    except Exception as e:
        st.session_state.pipeline_status = "error"
        st.session_state.error_message = str(e)

    pipeline_ready = st.session_state.pipeline_status == "ready"

    # Sidebar
    render_sidebar(pipeline_ready)

    # Hata durumu
    if not pipeline_ready:
        st.error(f"❌ Modeller yüklenemedi: {st.session_state.error_message}")
        st.info("Foundry Local kurulumunu ve model durumunu kontrol edin.")
        return

    # Chat geçmişi veya hoşgeldin kartı
    if st.session_state.messages:
        render_chat_history()
    else:
        render_welcome()

    # Giriş alanı
    question, send_clicked = render_input_area(pipeline_ready)

    # Soru gönderildi
    if send_clicked and question and question.strip():
        # Kullanıcı mesajını ekle
        st.session_state.messages.append({
            "role": "user",
            "content": question,
        })

        # Pipeline'ı çalıştır
        with st.spinner("🔍 Searching documents and generating answer..."):
            try:
                pipeline = st.session_state.pipeline
                # Son kullanıcı mesajından önceki konuşma geçmişini ilet
                history = st.session_state.messages[:-1] if len(st.session_state.messages) > 1 else []
                response = pipeline.ask(question, chat_history=history)

                if response.has_error and response.error == "empty_database":
                    bot_content = (
                        "⚠️ No documents have been loaded yet. "
                        "Please run `python ingest.py` first to index your documents."
                    )
                    sources = []
                elif response.has_error:
                    bot_content = f"❌ An error occurred: {response.error}"
                    sources = []
                else:
                    bot_content = response.answer
                    sources = response.unique_sources

            except ValueError as e:
                bot_content = f"⚠️ {e}"
                sources = []
            except Exception as e:
                bot_content = f"❌ Unexpected error: {e}"
                sources = []

        # Bot cevabını ekle
        st.session_state.messages.append({
            "role": "assistant",
            "content": bot_content,
            "sources": sources,
        })

        # Sayfayı yenile (yeni mesajları göster)
        st.rerun()


if __name__ == "__main__":
    main()
