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
    .chat-footer {
        position: fixed; bottom: 0; left: 0; right: 0;
        background: #0F1117; padding: 1rem 2rem;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.3); z-index: 100;
    }
    .chat-footer-inner { max-width: 800px; margin: 0 auto; }
    .stButton button[kind="secondary"] {
        border-radius: 20px !important; font-size: 0.85rem !important;
        padding: 0.25rem 1rem !important;
        background: #1A1D27 !important; color: #94A3B8 !important;
        border: 1px solid #2D3142 !important;
    }
    .stButton button[kind="secondary"]:hover {
        background: #242738 !important; color: #E2E8F0 !important;
    }
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

    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            is_ar = any("\u0600" <= c <= "\u06FF" for c in msg["content"])
            bubble_class = "user-bubble" if msg["role"] == "user" else "assistant-bubble"
            dir_attr = "rtl-text" if is_ar else "ltr-text"

            if msg["role"] == "user":
                st.markdown(
                    f'<div class="{bubble_class} {dir_attr}">'
                    f'{msg["content"]}'
                    f'</div><div class="clearfix"></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="{bubble_class} {dir_attr}">'
                    f'{msg["content"]}'
                    f'</div><div class="clearfix"></div>',
                    unsafe_allow_html=True,
                )

    st.markdown('<div style="height:100px;"></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Now generate response for pending user message (if any)
    _generate_response()

    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        quick_topics = [
            "💻 Web Development",
            "🤖 AI & ML",
            "🔒 Cybersecurity",
            "📊 Data Science",
        ]
        st.markdown(
            "<p style='text-align:center;font-size:0.85rem;color:#6B7A8F;'>"
            "أسئلة سريعة — Quick topics</p>",
            unsafe_allow_html=True,
        )
        cols = st.columns(4)
        for i, topic in enumerate(quick_topics):
            with cols[i]:
                if st.button(topic, key=f"qt_{i}", use_container_width=True,
                             type="secondary"):
                    _handle_user_input(topic)

    st.markdown('<div class="chat-footer"><div class="chat-footer-inner">', unsafe_allow_html=True)
    if prompt := st.chat_input("اكتب رسالتك هنا — Type your message here...", key="chat_input"):
        _handle_user_input(prompt)
    st.markdown('</div></div>', unsafe_allow_html=True)


def _handle_user_input(text: str):
    text = text.strip()
    if not text:
        return
    st.session_state.messages.append({"role": "user", "content": text})
    st.session_state.pending_response = True


def _generate_response():
    """Generate LLM response for the last user message if pending."""
    if not st.session_state.get("pending_response"):
        return
    st.session_state.pending_response = False

    if not st.session_state.messages:
        return
    last = st.session_state.messages[-1]
    if last["role"] != "user":
        return

    agent: SalesAgent = st.session_state.agent
    with st.spinner("جارٍ التفكير..." if any("\u0600" <= c <= "\u06FF" for c in last["content"]) else "Thinking..."):
        response = agent.generate_response(last["content"])
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
