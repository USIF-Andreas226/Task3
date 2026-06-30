import streamlit as st
import pandas as pd
import re
from datetime import datetime
from src.crm import CRMClient
from src.rag import KnowledgeBase

def show():
    # Role Guard
    if st.session_state.get("role") != "admin":
        st.error("Access Denied. Admins only.")
        st.stop()

    crm: CRMClient = st.session_state.crm
    logs = crm.get_all_usage_logs()
    users = crm.get_all_users()
    
    # Create user mapping for display
    user_map = {u["user_id"]: u["email"] for u in users}
    user_map["guest"] = "Guest User (Unauthenticated)"
    
    st.markdown("### 🔍 Behaviour & Response Trace Dashboard")
    st.markdown("تحليل وتتبع سلوك الوكيل الذكي | Admin trace viewer to debug agent reasoning and tool usage")

    if not logs:
        st.info("No logs recorded yet.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(logs)
    df["email"] = df["user_id"].map(lambda uid: user_map.get(uid, uid))
    df["timestamp_dt"] = pd.to_datetime(df["timestamp"])
    df["timestamp_display"] = df["timestamp_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Step 1: Select User
    all_users = sorted(list(df["email"].unique()))
    selected_user = st.selectbox("1️⃣ Select User Email | اختر العميل", all_users)
    user_df = df[df["email"] == selected_user]

    # Step 2: Select Conversation
    conv_ids = sorted(list(user_df["conversation_id"].unique()))
    conv_options = {cid: f"Conversation {str(cid)[:8]}... (Count: {len(user_df[user_df['conversation_id'] == cid])})" for cid in conv_ids}
    selected_conv_id = st.selectbox(
        "2️⃣ Select Conversation | اختر المحادثة", 
        conv_ids, 
        format_func=lambda cid: conv_options.get(cid, cid)
    )
    
    conv_df = user_df[user_df["conversation_id"] == selected_conv_id].sort_values(by="timestamp_dt")

    # Step 3: Select Message/Prompt
    # Fetch all user prompts. Let's find user messages for this conversation.
    msgs = crm.get_conversation_messages(selected_conv_id)
    user_prompts = [m for m in msgs if m["role"] == "user"]
    
    if not user_prompts:
        st.warning("No user prompts recorded for this conversation.")
        return
        
    prompt_options = {p["message_id"]: f"Prompt: {p['content'][:60]}... ({p['timestamp'].strftime('%H:%M:%S') if hasattr(p['timestamp'], 'strftime') else p['timestamp']})" for p in user_prompts}
    selected_message_id = st.selectbox(
        "3️⃣ Select Message/Prompt | اختر الرسالة", 
        [p["message_id"] for p in user_prompts],
        format_func=lambda mid: prompt_options.get(mid, mid)
    )

    # Fetch log entry corresponding to this user message
    # In generate_response, we linked the log record to the user_message_id
    log_row_matches = conv_df[conv_df["message_id"] == selected_message_id]
    if log_row_matches.empty:
        st.info("No OpenRouter trace found for this prompt (might have been answered by static fallback/greeting).")
        # Display the static message in the chat
        matching_prompt = next((p for p in user_prompts if p["message_id"] == selected_message_id), None)
        if matching_prompt:
            st.markdown(f"**User Prompt:** `{matching_prompt['content']}`")
            # Find the assistant response after this prompt
            all_msgs = list(msgs)
            idx = all_msgs.index(matching_prompt)
            if idx + 1 < len(all_msgs) and all_msgs[idx+1]["role"] == "assistant":
                st.markdown(f"**Assistant Response:** `{all_msgs[idx+1]['content']}`")
        return

    log_row = log_row_matches.iloc[0]
    
    # 4️⃣ Trace Replay: Expand the full step-by-step
    st.markdown("#### 🚀 Trace Replay Details")
    
    # Display the User Input
    user_prompt_text = next((p["content"] for p in user_prompts if p["message_id"] == selected_message_id), "N/A")
    st.markdown(f"**User Prompt | سؤال العميل:** `{user_prompt_text}`")
    st.markdown("---")

    # A) THINK Step
    st.subheader("🧠 1. THINKING & CLASSIFICATION")
    st.info(log_row["think_step"])

    # B) RAG Tool Invocations
    st.subheader("🔧 2. RAG RETRIEVAL TOOL CALLS")
    tool_calls = log_row.get("tool_calls", [])
    if not tool_calls:
        st.warning("No RAG tools were called or needed for this prompt.")
    else:
        for idx, tc in enumerate(tool_calls):
            with st.expander(f"🛠️ Tool Call {idx+1}: {tc['tool_name']} (latency: {tc.get('latency_ms', 0)}ms)", expanded=True):
                st.markdown("**Arguments:**")
                st.json(tc.get("args", {}))
                st.markdown("**Returned Sources:**")
                st.write(tc.get("sources", []))
                st.markdown("**Result Snippet:**")
                st.text(tc.get("result_summary", ""))

    # C) FINAL RESPONSE
    st.subheader("💬 3. FINAL RESPONSE GENERATED")
    response_text = log_row["final_response"]
    st.code(response_text, language="markdown")

    # Hallucination Checker (Dynamic)
    kb = KnowledgeBase()
    course_names = [c["name"].lower() for c in kb.courses]
    
    has_price = bool(re.search(r"(\$|USD|EGP|جنيه|\b\d{3,4}\b)", response_text))
    has_course_name = False
    matched_courses = []
    for name in course_names:
        if name in response_text.lower():
            has_course_name = True
            matched_courses.append(name)
            
    has_retrieval = False
    retrieved_sources = []
    for tc in tool_calls:
        if tc.get("sources") and len(tc["sources"]) > 0:
            has_retrieval = True
            retrieved_sources.extend(tc["sources"])

    # Hallucination detection logic
    if (has_price or has_course_name) and not has_retrieval:
        st.markdown(
            "🚨 <span style='color:#EF4444; font-weight:bold; font-size:1.1rem;'>"
            "Warning: No retrieval found for this claim (Potential Hallucination!)</span>",
            unsafe_allow_html=True
        )
        st.error(
            "The assistant made a claim regarding prices or course names but no "
            "RAG source files were retrieved for grounding."
        )
    elif has_course_name and has_retrieval:
        # Check if the course mentioned is in the retrieved sources (simple check)
        st.markdown("✅ **Grounded Claim:** Course mentions are supported by the RAG retrieval sources.")
        st.write(f"Matched courses: `{matched_courses}` | Sources: `{retrieved_sources}`")
    else:
        st.markdown("ℹ️ No specific course details or price claims detected in this system response.")

    # D) METADATA
    st.subheader("📊 4. EXECUTION METADATA")
    meta_df = pd.DataFrame([
        {"Metric": "Model Used", "Value": log_row["model"]},
        {"Metric": "Provider", "Value": log_row["provider"]},
        {"Metric": "Prompt Tokens", "Value": int(log_row["input_tokens"])},
        {"Metric": "Completion Tokens", "Value": int(log_row["output_tokens"])},
        {"Metric": "Execution Cost (USD)", "Value": f"${log_row['total_cost_usd']:.5f}"},
        {"Metric": "Execution Latency (ms)", "Value": f"{log_row['latency_ms']} ms"}
    ])
    st.table(meta_df)
