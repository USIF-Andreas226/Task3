import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Kayfa — AI Sales Agent",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Cairo', sans-serif; }
    .stApp { background-color: #F0F4F8; }
    .main-header {
        text-align: center; padding: 2rem 0 1rem; color: #1E3A5F;
        font-size: 2rem; font-weight: 700;
    }
    .sub-header {
        text-align: center; color: #4A6FA5; font-size: 1rem; margin-bottom: 2rem;
    }
    div[data-testid="stSidebarNav"] { display: none; }
    .custom-nav {
        display: flex; justify-content: center; gap: 1rem; margin: 1rem 0 2rem;
    }
    .custom-nav a {
        text-decoration: none; padding: 0.75rem 2rem; border-radius: 30px;
        font-weight: 600; font-size: 1rem; transition: all 0.3s;
    }
    .custom-nav a.nav-active {
        background: #1E3A5F; color: white;
    }
    .custom-nav a.nav-inactive {
        background: white; color: #1E3A5F; border: 2px solid #1E3A5F;
    }
    .custom-nav a:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
    .logo-text { font-size: 1.5rem; font-weight: 700; color: #1E3A5F; text-align: center; }
    .logout-btn { position: fixed; top: 10px; right: 10px; z-index: 999; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="logo-text">🎓 Kayfa — AI Sales Agent</div>', unsafe_allow_html=True)
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
LOGIN_PASSWORD = os.environ.get("LOGIN_PASSWORD",
    st.secrets.get("login_password", "REDACTED_LOGIN_PASSWORD"))

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
