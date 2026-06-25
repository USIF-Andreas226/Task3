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


def show():
    initialize_session()

    st.markdown("""
<style>
    div[data-testid="InputInstructions"] { display: none; }
    .stChatInputContainer { border-radius: 24px !important; border: 1px solid #2D3142 !important; background: #1A1D27 !important; }
    .stChatInputContainer input { background: #1A1D27 !important; color: #E2E8F0 !important; }
    .stChatFloatingInputContainer { bottom: 0; padding: 1rem 2rem; background: #0F1117; box-shadow: 0 -2px 10px rgba(0,0,0,0.3); }
    div[data-testid="stChatMessage"] {
        padding: 12px 18px !important; margin: 8px 0 !important;
        max-width: 85% !important; font-size: 1rem !important; line-height: 1.7 !important;
        border-radius: 20px !important;
    }
    div[data-testid="stChatMessage"][data-testid="stChatMessage"][aria-label="user"] {
        background: linear-gradient(135deg, #2563EB 0%, #3B82F6 100%) !important;
        color: #FFFFFF !important;
        border-radius: 20px 20px 5px 20px !important;
        margin-left: auto !important;
    }
    div[data-testid="stChatMessage"][aria-label="user"] * { color: #FFFFFF !important; }
    div[data-testid="stChatMessage"][aria-label="assistant"] {
        background: #1A1D27 !important; color: #E2E8F0 !important;
        border: 1px solid #2D3142 !important;
        border-radius: 20px 20px 20px 5px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
    }
    div[data-testid="stChatMessage"][aria-label="assistant"] * { color: #E2E8F0 !important; }
    div[data-testid="stChatMessage"][aria-label="assistant"] strong { color: #93C5FD !important; }
    .greeting-banner {
        background: linear-gradient(135deg, #1E293B 0%, #1A1D27 100%);
        border: 1px solid #2D3142; border-radius: 16px; padding: 2rem;
        margin: 1rem auto; max-width: 700px; text-align: center;
    }
    .greeting-banner h4 { color: #93C5FD !important; }
    .greeting-banner p { color: #94A3B8 !important; }
</style>
    """, unsafe_allow_html=True)

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
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if prompt := st.chat_input("اكتب رسالتك هنا — Type your message here..."):
        prompt = prompt.strip()
        if not prompt:
            return

        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("جارٍ التفكير..." if any("\u0600" <= c <= "\u06FF" for c in prompt) else "Thinking..."):
                agent: SalesAgent = st.session_state.agent
                response = agent.generate_response(prompt)
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
