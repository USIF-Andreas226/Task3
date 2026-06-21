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
    .stChatMessage { border-radius: 16px; padding: 0.75rem 1rem; }
    [data-testid="stChatMessageContent"] {
        font-size: 1rem; line-height: 1.6;
    }
    .rtl-text { direction: rtl; text-align: right; font-family: 'Cairo', sans-serif; }
    .ltr-text { direction: ltr; text-align: left; }
    div[data-testid="InputInstructions"] { display: none; }
    .stChatInputContainer { border-radius: 24px; border: 2px solid #1E3A5F; }
    .st-emotion-cache-janbn0 { border-radius: 24px; }
    .user-bubble {
        background: linear-gradient(135deg, #1E3A5F 0%, #2A5298 100%);
        color: white; border-radius: 20px 20px 5px 20px;
        padding: 12px 18px; margin: 8px 0; max-width: 85%;
        float: right; clear: both;
    }
    .assistant-bubble {
        background: white; border: 1px solid #E0E7EF; border-radius: 20px 20px 20px 5px;
        padding: 12px 18px; margin: 8px 0; max-width: 85%;
        float: left; clear: both; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .chat-area { padding: 1rem 0; overflow-y: auto; }
    .clearfix::after { content: ""; display: table; clear: both; }
    .greeting-banner {
        background: linear-gradient(135deg, #E8F0FE 0%, #F0F4FF 100%);
        border: 1px solid #C5D5E8; border-radius: 16px; padding: 2rem;
        margin: 1rem auto; max-width: 700px; text-align: center;
    }
    .chat-footer {
        position: fixed; bottom: 0; left: 0; right: 0;
        background: white; padding: 1rem 2rem; box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
        z-index: 100;
    }
    .chat-footer-inner { max-width: 800px; margin: 0 auto; }
    .stButton button[kind="secondary"] {
        border-radius: 20px; font-size: 0.85rem; padding: 0.25rem 1rem;
    }
    .quick-reply-btn { margin: 0.25rem; }
    @media (max-width: 768px) {
        .user-bubble, .assistant-bubble { max-width: 95%; }
    }
</style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    st.markdown(
        "<h3 style='text-align:center;color:#1E3A5F;margin-bottom:0;'>"
        "💬 تحدث مع مستشار كايفة — Talk to Kayfa Advisor</h3>",
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
            '<h4 style="color:#1E3A5F;">مرحباً بك في كايفة!</h4>'
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
    if not text.strip():
        return

    st.session_state.messages.append({"role": "user", "content": text.strip()})

    agent: SalesAgent = st.session_state.agent
    with st.spinner("جارٍ التفكير..." if any("\u0600" <= c <= "\u06FF" for c in text) else "Thinking..."):
        response = agent.generate_response(text.strip())

    st.session_state.messages.append({"role": "assistant", "content": response})

    st.rerun()
