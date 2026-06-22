import streamlit as st
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env and .env.local (local dev only)
load_dotenv()
env_local = Path(__file__).parent / ".env.local"
if env_local.exists():
    load_dotenv(dotenv_path=env_local)

# Streamlit Cloud: inject secrets into environment for sub-modules (agent.py, crm.py)
for _key in ["OPENROUTER_API_KEY", "OPENROUTER_MODEL", "MONGO_URI", "MONGO_DB", "MONGO_COLLECTION"]:
    if _key not in os.environ:
        val = st.secrets.get(_key)
        if val:
            os.environ[_key] = val

st.set_page_config(
    page_title="Kayf — AI Sales Agent",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
    :root {
        --kf-primary: #3B82F6;  /* bright blue */
        --kf-accent: #60A5FA;   /* light blue */
        --kf-bg: #0F1117;       /* page background (near black) */
        --kf-panel: #1A1D27;    /* card background */
        --kf-text: #E2E8F0;     /* primary text */
        --kf-muted: #94A3B8;    /* secondary text */
        --kf-border: #2D3142;   /* border color */
        --kf-input-bg: #242738; /* input background */
    }
    * { font-family: 'Cairo', sans-serif; color: var(--kf-text); }
    body, .stApp { background-color: var(--kf-bg) !important; }
    .main-header {
        text-align: center; padding: 2rem 0 1rem; color: var(--kf-accent);
        font-size: 2rem; font-weight: 700;
    }
    .sub-header {
        text-align: center; color: var(--kf-muted); font-size: 1rem; margin-bottom: 2rem;
    }
    div[data-testid="stSidebarNav"] { display: none; }
    section[data-testid="stSidebar"] { display: none !important; }
    div[data-testid="collapsedControl"] { display: none !important; }
    header[data-testid="stHeader"] { display: none; }
    .main > div { padding-left: 0 !important; padding-right: 0 !important; }
    .custom-nav {
        display: flex; justify-content: center; gap: 1rem; margin: 1rem 0 2rem;
    }
    .custom-nav a {
        text-decoration: none; padding: 0.75rem 2rem; border-radius: 30px;
        font-weight: 600; font-size: 1rem; transition: all 0.18s ease;
        background: var(--kf-panel); color: var(--kf-accent); border: 1px solid var(--kf-border);
    }
    .custom-nav a.nav-active {
        background: linear-gradient(90deg,var(--kf-primary),#2563EB); color: white; box-shadow: 0 6px 18px rgba(59,130,246,0.2);
    }
    .custom-nav a.nav-inactive {
        background: var(--kf-panel); color: var(--kf-muted); border: 1px solid var(--kf-border);
    }
    .custom-nav a:hover { transform: translateY(-3px); box-shadow: 0 8px 26px rgba(0,0,0,0.3); }
    .logo-text { font-size: 1.5rem; font-weight: 700; color: var(--kf-accent); text-align: center; }
    .logout-btn { position: fixed; top: 10px; right: 10px; z-index: 999; }
    .login-container { background: var(--kf-panel); color: var(--kf-text); border: 1px solid var(--kf-border); border-radius: 20px; }

    /* Form controls and labels */
    label, .stMarkdown, .stText, .stTextInput label, .stTextArea label, .stSelectbox label {
        color: var(--kf-accent) !important;
        font-weight: 500 !important;
        display: block !important;
        margin-bottom: 0.5rem !important;
    }
    input, textarea, select {
        background: var(--kf-input-bg) !important;
        color: var(--kf-text) !important;
        border: 1px solid var(--kf-border) !important;
        border-radius: 8px !important;
        padding: 10px 12px !important;
        box-shadow: none !important;
        font-size: 1rem !important;
    }
    input::placeholder, textarea::placeholder { color: #64748B !important; opacity: 1 !important; }
    input:focus, textarea:focus, select:focus {
        border-color: var(--kf-primary) !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
    }
    .stButton>button, button {
        background: linear-gradient(90deg,var(--kf-primary),#2563EB) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
    }
    .stButton>button:hover { filter: brightness(1.1) !important; }
    .stButton>button[kind="secondary"] {
        background: var(--kf-panel) !important;
        color: var(--kf-accent) !important;
        border: 1px solid var(--kf-border) !important;
    }
    .login-container input, .login-container textarea {
        border: 1px solid var(--kf-border) !important;
        background: var(--kf-input-bg) !important;
        color: var(--kf-text) !important;
    }
    .login-container label {
        color: var(--kf-accent) !important;
        font-weight: 600 !important;
    }
    /* Streamlit default element overrides */
    .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, span:not(.user-bubble *):not(.assistant-bubble *) {
        color: var(--kf-text) !important;
    }
    div.stForm { background: transparent !important; border: none !important; }
    .stAlert { background: var(--kf-panel) !important; color: var(--kf-text) !important; border: 1px solid var(--kf-border) !important; }
    .stSpinner > div { border-color: var(--kf-primary) !important; }
    .st-emotion-cache-1kyx7za, .st-emotion-cache-1wmy9hl, .st-emotion-cache-1avcm0n { background: var(--kf-bg) !important; }
</style>
    """, unsafe_allow_html=True)

st.markdown('<div class="logo-text">🎓 Kayf — AI Sales Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">مساعد المبيعات الذكي | Smart Sales Assistant</div>', unsafe_allow_html=True)

page = st.session_state.get("page", "chat")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📞  Chat Agent", use_container_width=True,
                     type="primary" if page == "chat" else "secondary"):
            st.session_state.page = "chat"
            st.rerun()
    with c2:
        if st.button("📋  CRM Tickets", use_container_width=True,
                     type="primary" if page == "crm" else "secondary"):
            st.session_state.page = "crm"
            st.rerun()

LOGIN_USERNAME = os.environ.get("LOGIN_USERNAME",
    st.secrets.get("login_username", "admin"))
# For development/testing, use safe default. In production, set via environment or Streamlit secrets.
# IMPORTANT: Change these credentials in production via: environment variables or st.secrets
LOGIN_PASSWORD = os.environ.get("LOGIN_PASSWORD",
    st.secrets.get("login_password", "test123"))

if page == "crm" and "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if page == "crm" and not st.session_state.authenticated:
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px; margin: 8rem auto; padding: 2rem;
            background: white; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            text-align: center;
        }
        .login-logo { font-size: 3rem; margin-bottom: 0.5rem; }
        .login-title { font-size: 1.3rem; font-weight: 700; color: #1E3A5F; margin-bottom: 0.25rem; }
        .login-subtitle { font-size: 0.9rem; color: #6B7A8F; margin-bottom: 1.5rem; }
    </style>
    <div class="login-container">
        <div class="login-logo">🔒</div>
        <div class="login-title">CRM — تسجيل الدخول</div>
        <div class="login-subtitle">يرجى تسجيل الدخول لعرض تذاكر CRM</div>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("🔑  Sign In", use_container_width=True, type="primary")
            if submitted:
                if username == LOGIN_USERNAME and password == LOGIN_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    st.stop()

if page == "chat":
    import pages.chat_agent
    pages.chat_agent.show()
else:
    import pages.crm_tickets
    pages.crm_tickets.show()
