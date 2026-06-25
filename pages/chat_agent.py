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
