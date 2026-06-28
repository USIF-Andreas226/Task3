import streamlit as st
import os
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env and .env.local (local dev only)
load_dotenv()
env_local = Path(__file__).parent / ".env.local"
if env_local.exists():
    load_dotenv(dotenv_path=env_local)

# Streamlit Cloud: inject secrets into environment for sub-modules (agent.py, crm.py)
for _key in ["GROQ_API_KEY", "GROQ_MODEL", "MONGO_URI", "MONGO_DB", "MONGO_COLLECTION",
             "LOGIN_USERNAME", "LOGIN_PASSWORD",
             "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM", "SALES_NUMBER_1"]:
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
from src.crm import CRMClient

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

# Initialize database client
if "crm" not in st.session_state:
    st.session_state.crm = CRMClient()
crm = st.session_state.crm

# Initialize WhatsApp reporter (no APScheduler — Streamlit-safe)
if "whatsapp" not in st.session_state:
    try:
        from src.whatsapp import WhatsAppReporter
        st.session_state.whatsapp = WhatsAppReporter(crm)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to init WhatsApp reporter: {e}")

# Streamlit-safe daily report trigger (checked on each interaction)
if "whatsapp" in st.session_state and st.session_state.whatsapp.client:
    reporter = st.session_state.whatsapp
    now = datetime.now()
    last_sent = st.session_state.get("last_report_sent")

    should_send = (
        now.hour == 8 and now.minute < 5
        and (last_sent is None or (now - last_sent).days >= 1)
    )

    if should_send:
        reporter.send_report()
        st.session_state.last_report_sent = now

import re

# Check global authentication
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.markdown("""
    <div style="max-width: 450px; margin: 3rem auto 1rem; text-align: center;">
        <div style="font-size: 3.5rem; margin-bottom: 0.5rem;">🔒</div>
        <h3 style="color: var(--kf-accent); font-weight: 700; margin-bottom: 0.2rem;">Kayf Sales Advisor</h3>
        <p style="color: var(--kf-muted); font-size: 0.9rem;">تسجيل الدخول أو إنشاء حساب | Login or Sign Up</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2.5, 1])
    with col2:
        tab_login, tab_signup = st.tabs(["🔑 تسجيل الدخول | Login", "📝 حساب جديد | Sign Up"])
        
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("البريد الإلكتروني | Email", placeholder="yourname@example.com")
                password = st.text_input("كلمة المرور | Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("🔑 تسجيل الدخول | Sign In", use_container_width=True, type="primary")
                
                if submitted:
                    email = email.strip().lower()
                    if not email or not password:
                        st.error("يرجى ملء جميع الحقول | Please fill all fields")
                    else:
                        user = crm.verify_user(email, password)
                        if user:
                            st.session_state.authenticated = True
                            st.session_state.user_id = user["user_id"]
                            st.session_state.role = user["role"]
                            st.session_state.page = "chat"
                            st.success("تم تسجيل الدخول بنجاح! | Login successful!")
                            st.rerun()
                        else:
                            st.error("البريد الإلكتروني أو كلمة المرور غير صحيحة | Invalid email or password")
                            
        with tab_signup:
            with st.form("signup_form"):
                new_email = st.text_input("البريد الإلكتروني | Email", placeholder="yourname@example.com")
                new_password = st.text_input("كلمة المرور | Password", type="password", placeholder="••••••••")
                confirm_password = st.text_input("تأكيد كلمة المرور | Confirm Password", type="password", placeholder="••••••••")
                role = st.selectbox("الدور | Role", ["user", "admin"])
                signup_submitted = st.form_submit_button("📝 إنشاء حساب | Sign Up", use_container_width=True, type="primary")
                
                if signup_submitted:
                    new_email = new_email.strip().lower()
                    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
                    if not new_email or not new_password or not confirm_password:
                        st.error("يرجى ملء جميع الحقول | Please fill all fields")
                    elif not re.match(email_pattern, new_email):
                        st.error("البريد الإلكتروني غير صالح | Invalid email address")
                    elif len(new_password) < 6:
                        st.error("يجب أن تكون كلمة المرور 6 أحرف على الأقل | Password must be at least 6 characters")
                    elif new_password != confirm_password:
                        st.error("كلمات المرور غير متطابقة | Passwords do not match")
                    else:
                        user = crm.create_user(new_email, new_password, role)
                        if user:
                            st.session_state.authenticated = True
                            st.session_state.user_id = user["user_id"]
                            st.session_state.role = user["role"]
                            st.session_state.page = "chat"
                            st.success("تم إنشاء الحساب بنجاح! | Sign up successful!")
                            st.rerun()
                        else:
                            st.error("البريد الإلكتروني مسجل بالفعل | Email already registered")
    st.stop()

# --- Authenticated App Layout ---
page = st.session_state.get("page", "chat")

# Top bar layout with logo and logout
col_logo, col_logout = st.columns([8, 2])
with col_logo:
    st.markdown('<div class="logo-text" style="text-align: left; padding: 10px;">🎓 Kayf — AI Sales Agent</div>', unsafe_allow_html=True)
with col_logout:
    if st.button("🚪 تسجيل الخروج | Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.role = None
        st.session_state.page = "chat"
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.rerun()

# Navigation Bar based on Role Guard
if st.session_state.get("role") == "admin":
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("📞 Chat Agent", use_container_width=True, type="primary" if page == "chat" else "secondary"):
                st.session_state.page = "chat"
                st.rerun()
        with c2:
            if st.button("📋 CRM Tickets", use_container_width=True, type="primary" if page == "crm" else "secondary"):
                st.session_state.page = "crm"
                st.rerun()
        with c3:
            if st.button("💰 Cost Monitor", use_container_width=True, type="primary" if page == "cost" else "secondary"):
                st.session_state.page = "cost"
                st.rerun()
        with c4:
            if st.button("🔍 Response Trace", use_container_width=True, type="primary" if page == "trace" else "secondary"):
                st.session_state.page = "trace"
                st.rerun()
    st.divider()
    if "whatsapp" in st.session_state:
        if st.button("📱 Test WhatsApp Report Now", use_container_width=True):
            try:
                st.session_state.whatsapp.send_report()
                st.success("✅ WhatsApp report sent!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
else:
    st.session_state.page = "chat"
    page = "chat"

# Render selected page
if page == "chat":
    import pages.chat_agent
    pages.chat_agent.show()
elif page == "crm":
    import pages.crm_tickets
    pages.crm_tickets.show()
elif page == "cost":
    import pages.monitoring_cost
    pages.monitoring_cost.show()
elif page == "trace":
    import pages.monitoring_trace
    pages.monitoring_trace.show()
