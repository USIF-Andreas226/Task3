import streamlit as st
import pandas as pd
from datetime import datetime, date
from src.crm import CRMClient

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
    
    st.markdown("### 💰 Cost & Token Usage Monitor")
    st.markdown("تحليل تكاليف الاستخدام والرموز المستهلكة | Admin dashboard to track LLM costs and token usage")

    if not logs:
        st.info("No usage logs recorded yet.")
        return

    # Convert logs to Pandas DataFrame for easy analysis
    df = pd.DataFrame(logs)
    
    # Map user emails
    df["email"] = df["user_id"].map(lambda uid: user_map.get(uid, uid))
    
    # Format dates
    df["timestamp_dt"] = pd.to_datetime(df["timestamp"])
    df["timestamp_display"] = df["timestamp_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # A) Summary Cards (top row)
    total_spend = df["total_cost_usd"].sum()
    total_convs = df["conversation_id"].nunique()
    total_msgs = len(df)
    avg_cost_conv = total_spend / total_convs if total_convs > 0 else 0.0

    st.markdown("#### 📊 System Summary Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Spend", f"${total_spend:.5f}")
    with col2:
        st.metric("Total Conversations", f"{total_convs}")
    with col3:
        st.metric("Total Messages", f"{total_msgs}")
    with col4:
        st.metric("Avg Cost / Conv", f"${avg_cost_conv:.5f}")

    # Layout for Provider Breakdown and Filter Controls
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("#### 🏢 Provider Breakdown")
        rag_notes = "Pure Python TF-IDF/Fuzzy RAG"
        provider_df = pd.DataFrame([
            {"Service": "LLM Generation (OpenRouter)", "Cost": f"${df['llm_cost_usd'].sum():.5f}", "Notes": "OpenRouter API Calls"},
            {"Service": "RAG Embeddings (Local)", "Cost": "$0.00000", "Notes": f"Free ({rag_notes})"},
            {"Service": "Total Combined", "Cost": f"${total_spend:.5f}", "Notes": "Grand Total"}
        ])
        st.table(provider_df)

    with c2:
        st.markdown("#### 🔍 Filter Operations")
        # Filter by User
        all_emails = ["All Users"] + sorted(list(df["email"].unique()))
        selected_user = st.selectbox("Filter by User Email", all_emails)
        
        # Filter by Date
        min_date = df["timestamp_dt"].min().date()
        max_date = df["timestamp_dt"].max().date()
        
        # Guard against equal min and max
        if min_date == max_date:
            date_range = [min_date, max_date]
            st.text(f"Logging date: {min_date}")
        else:
            date_range = st.date_input("Filter by Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

    # Apply filters
    filtered_df = df.copy()
    if selected_user != "All Users":
        filtered_df = filtered_df[filtered_df["email"] == selected_user]
        
    if len(date_range) == 2:
        start_d, end_d = date_range
        filtered_df = filtered_df[(filtered_df["timestamp_dt"].dt.date >= start_d) & (filtered_df["timestamp_dt"].dt.date <= end_d)]

    # B) Per-Message Table
    st.markdown("#### 💬 Per-Message Costs & Tokens (Sorted by Cost Descending)")
    msg_display_df = filtered_df[[
        "timestamp_display", "email", "model", "input_tokens", "output_tokens", "total_cost_usd", "latency_ms"
    ]].rename(columns={
        "timestamp_display": "Timestamp",
        "email": "User Email",
        "model": "Model Used",
        "input_tokens": "Prompt Tokens",
        "output_tokens": "Completion Tokens",
        "total_cost_usd": "Cost (USD)",
        "latency_ms": "Latency (ms)"
    })
    # Sort by Cost Descending
    msg_display_df = msg_display_df.sort_values(by="Cost (USD)", ascending=False)
    st.dataframe(msg_display_df, use_container_width=True)

    # C) Per-Conversation Rollup
    st.markdown("#### 📂 Per-Conversation Rollup")
    conv_rollup = df.groupby("conversation_id").agg({
        "email": "first",
        "message_id": "count",
        "input_tokens": "sum",
        "output_tokens": "sum",
        "total_cost_usd": "sum"
    }).reset_index().rename(columns={
        "conversation_id": "Conversation ID",
        "email": "User",
        "message_id": "Message Count",
        "input_tokens": "Total Input Tokens",
        "output_tokens": "Total Output Tokens",
        "total_cost_usd": "Total Cost (USD)"
    })
    
    # Shorten Conversation ID for display
    conv_rollup["Conversation ID (Short)"] = conv_rollup["Conversation ID"].map(lambda x: x[:8] + "...")
    # Reorder columns
    conv_rollup = conv_rollup[["Conversation ID", "Conversation ID (Short)", "User", "Message Count", "Total Input Tokens", "Total Output Tokens", "Total Cost (USD)"]]
    
    st.dataframe(conv_rollup.drop(columns=["Conversation ID"]), use_container_width=True)

    # Click to drill into individual message costs
    selected_conv_short = st.selectbox(
        "Drill into Conversation Details (Select ID)", 
        ["None"] + list(conv_rollup["Conversation ID"].unique())
    )
    if selected_conv_short != "None":
        st.markdown(f"##### Details for Conversation `{selected_conv_short}`")
        detail_df = df[df["conversation_id"] == selected_conv_short].sort_values(by="timestamp_dt")
        for i, row in detail_df.iterrows():
            with st.container():
                st.markdown(f"**Turn {i+1}** - {row['timestamp_display']} | Model: `{row['model']}`")
                st.markdown(f"- **Cost:** `${row['total_cost_usd']:.5f}` | **Tokens:** {row['input_tokens']} in / {row['output_tokens']} out | **Latency:** {row['latency_ms']} ms")
                st.text_area("Final Assistant Response", row["final_response"], height=80, key=f"resp_{row['log_id']}")
                st.markdown("---")

    # D) Per-User Rollup
    st.markdown("#### 👤 Per-User Cost Ranking")
    user_rollup = df.groupby("email").agg({
        "conversation_id": "nunique",
        "message_id": "count",
        "input_tokens": "sum",
        "output_tokens": "sum",
        "total_cost_usd": "sum"
    }).reset_index().rename(columns={
        "email": "User Email",
        "conversation_id": "Conversation Count",
        "message_id": "Total Messages",
        "input_tokens": "Total Input Tokens",
        "output_tokens": "Total Output Tokens",
        "total_cost_usd": "Total Spend (USD)"
    }).sort_values(by="Total Spend (USD)", ascending=False)
    
    st.dataframe(user_rollup, use_container_width=True)
