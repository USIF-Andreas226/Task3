import streamlit as st
from src.rag import KnowledgeBase
from src.crm import CRMClient
from src.agent import SalesAgent


def initialize_session():
    if "agent" not in st.session_state:
        kb = KnowledgeBase()
        crm = st.session_state.get("crm", CRMClient())
        st.session_state.agent = SalesAgent(kb, crm)
        st.session_state.crm = crm
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "step" not in st.session_state:
        st.session_state.step = "input"


def show():
    initialize_session()

    step = st.session_state.step

    # --- Step: respond → LLM call ---
    if step == "respond":
        st.session_state.step = "input"
        if st.session_state.messages:
            last = st.session_state.messages[-1]
            if last["role"] == "user":
                agent: SalesAgent = st.session_state.agent
                response = agent.generate_response(last["content"])
                st.session_state.messages.append({"role": "assistant", "content": response})

    # --- Render all messages ---
    _render_ui()

    # --- Step: collect_new → append user msg and queue LLM for next run ---
    if step == "collect_new":
        st.session_state.step = "respond"

    # --- Accept new input ---
    if prompt := st.chat_input("اكتب رسالتك هنا — Type your message here...", key="chat_input"):
        prompt = prompt.strip()
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.step = "collect_new"
            st.rerun()


def _render_ui():
    st.markdown("""
<style>
    .chat-container { max-width: 800px; margin: 0 auto; padding: 0 1rem; }
    .rtl-text { direction: rtl; text-align: right; font-family: 'Cairo', sans-serif; }
    .ltr-text { direction: ltr; text-align: left; }
    div[data-testid="InputInstructions"] { display: none; }
    .stChatInputContainer { border-radius: 24px !important; border: 1px solid #2D3142 !important; background: #1A1D27 !important; }
    .st-emotion-cache-janbn0 { border-radius: 24px !important; }
    .stChatInputContainer input { background: #1A1D27 !important; color: #E2E8F0 !important; }
    .user-bubble {
        background: linear-gradient(135deg, #2563EB 0%, #3B82F6 100%) !important;
        color: #FFFFFF !important;
        border-radius: 20px 20px 5px 20px !important;
        padding: 12px 18px !important; margin: 8px 0 !important;
        max-width: 85% !important; float: right !important; clear: both !important;
        font-size: 1rem !important; line-height: 1.7 !important;
        font-weight: 500 !important;
    }
    .user-bubble * { color: #FFFFFF !important; }
    .assistant-bubble {
        background: #1A1D27 !important;
        color: #E2E8F0 !important;
        border: 1px solid #2D3142 !important;
        border-radius: 20px 20px 20px 5px !important;
        padding: 12px 18px !important; margin: 8px 0 !important;
        max-width: 85% !important; float: left !important; clear: both !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
        font-size: 1rem !important; line-height: 1.7 !important;
        font-weight: 400 !important;
    }
    .assistant-bubble * { color: #E2E8F0 !important; }
    .assistant-bubble strong { color: #93C5FD !important; font-weight: 700 !important; }
    .clearfix::after { content: ""; display: table; clear: both; }
    .greeting-banner {
        background: linear-gradient(135deg, #1E293B 0%, #1A1D27 100%);
        border: 1px solid #2D3142; border-radius: 16px; padding: 2rem;
        margin: 1rem auto; max-width: 700px; text-align: center;
    }
    .greeting-banner h4 { color: #93C5FD !important; }
    .greeting-banner p { color: #94A3B8 !important; }
    @media (max-width: 768px) {
        .user-bubble, .assistant-bubble { max-width: 95% !important; }
    }
</style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    st.markdown(
        "<h3 style='text-align:center;color:#1E3A5F;margin-bottom:0;'>"
        "💬 تحدث مع مستشار كيف — Talk to Kayf Advisor</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#6B7A8F;font-size:0.9rem;margin-top:0;'>"
        "اطرح أي سؤال — الكورسات، المسارات، الدبلومات، الأسعار، أو أي استفسار"
        "<br>Ask about courses, tracks, diplomas, prices, or anything else</p>",
        unsafe_allow_html=True,
    )

    if not st.session_state.messages:
        st.markdown(
            '<div class="greeting-banner">'
            '<div style="font-size:3rem;margin-bottom:1rem;">🎓</div>'
            '<h4 style="color:#1E3A5F;">مرحباً بك في كيف!</h4>'
            '<p style="color:#4A6FA5;">أنا مساعدك الشخصي. كيف أقدر أساعدك اليوم؟</p>'
            '<p style="color:#4A6FA5;font-size:0.9rem;">I\'m your personal assistant. How can I help you today?</p>'
        , unsafe_allow_html=True)
    else:
        for msg in st.session_state.messages:
            is_ar = any("\u0600" <= c <= "\u06FF" for c in msg["content"])
            bubble_class = "user-bubble" if msg["role"] == "user" else "assistant-bubble"
            dir_attr = "rtl-text" if is_ar else "ltr-text"
            st.markdown(
                f'<div class="{bubble_class} {dir_attr}">'
                f'{msg["content"]}'
                f'</div><div class="clearfix"></div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div style="height:100px;"></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
