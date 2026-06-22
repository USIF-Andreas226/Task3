import streamlit as st
from src.crm import CRMClient


def show():
    st.markdown("""
<style>
    .crm-container { max-width: 1200px; margin: 0 auto; padding: 0 1rem; }
    .ticket-card {
        background: #1A1D27; border-radius: 16px; padding: 1.5rem; margin: 1rem 0;
        border: 1px solid #2D3142; box-shadow: 0 2px 12px rgba(0,0,0,0.2);
        direction: rtl; text-align: right;
    }
    .ticket-card.en { direction: ltr; text-align: left; }
    .ticket-header {
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 1rem; padding-bottom: 0.75rem;
        border-bottom: 1px solid #2D3142;
    }
    .ticket-id { font-size: 1.1rem; font-weight: 700; color: #93C5FD; }
    .ticket-temp {
        padding: 0.3rem 1rem; border-radius: 20px; font-size: 0.85rem; font-weight: 600;
    }
    .temp-hot { background: #4A1C1C; color: #FF8A80; }
    .temp-warm { background: #3D2E1A; color: #FFB74D; }
    .temp-cold { background: #1A2744; color: #64B5F6; }
    .ticket-section {
        margin: 0.75rem 0; padding: 0.75rem; background: #242738; border-radius: 10px;
    }
    .ticket-section-title {
        font-weight: 600; color: #93C5FD; margin-bottom: 0.5rem; font-size: 0.95rem;
    }
    .ticket-field { margin: 0.4rem 0; font-size: 0.9rem; }
    .ticket-label { color: #94A3B8; font-weight: 500; }
    .ticket-value { color: #E2E8F0; }
    .signal-badge {
        display: inline-block; padding: 0.2rem 0.6rem; border-radius: 12px;
        background: #1B3D2A; color: #81C784; font-size: 0.8rem; margin: 0.15rem;
    }
    .no-tickets {
        text-align: center; padding: 4rem 2rem; color: #94A3B8;
    }
    .stats-grid {
        display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem; margin: 1rem 0;
    }
    .stat-card {
        background: #1A1D27; border-radius: 12px; padding: 1.25rem; text-align: center;
        border: 1px solid #2D3142;
    }
    .stat-number { font-size: 2rem; font-weight: 700; color: #93C5FD; }
    .stat-label { font-size: 0.85rem; color: #94A3B8; margin-top: 0.25rem; }
    .summary-text { line-height: 1.7; color: #E2E8F0; font-size: 0.95rem; }
    .arabic-ar { direction: rtl; text-align: right; }
    .arabic-en { direction: ltr; text-align: left; }
</style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="crm-container">', unsafe_allow_html=True)
    st.markdown(
        "<h3 style='text-align:center;color:#1E3A5F;margin-bottom:0.25rem;'>"
        "📋  تذاكر CRM — Sales Leads</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#6B7A8F;font-size:0.9rem;'>"
        "جميع العملاء المحتملين — All captured leads for the sales team</p>",
        unsafe_allow_html=True,
    )

    crm = st.session_state.get("crm", CRMClient())
    st.session_state.crm = crm

    if st.button("🔄  تحديث — Refresh", use_container_width=False, type="secondary"):
        st.rerun()

    tickets = crm.get_all_tickets()

    if not tickets:
        st.markdown(
            '<div class="no-tickets">'
            '<div style="font-size:3rem;">📭</div>'
            '<h4>لا توجد تذاكر بعد</h4>'
            '<p>عندما يحدد الوكيل عميلاً محتملاً، ستظهر تذكرته هنا</p>'
            '<p style="font-size:0.85rem;">When the agent detects a qualified lead, tickets will appear here</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)
        return

    hot = sum(1 for t in tickets if t.get("assessment", {}).get("temperature") == "hot")
    warm = sum(1 for t in tickets if t.get("assessment", {}).get("temperature") == "warm")
    cold = sum(1 for t in tickets if t.get("assessment", {}).get("temperature") == "cold")

    st.markdown('<div class="stats-grid">', unsafe_allow_html=True)
    for label, count, color in [
        ("🔥 ساخن — Hot", hot, "#D32F2F"),
        ("💡 دافئ — Warm", warm, "#E65100"),
        ("🧊 بارد — Cold", cold, "#1565C0"),
        ("📊 المجموع — Total", len(tickets), "#1E3A5F"),
    ]:
        st.markdown(
            f'<div class="stat-card">'
            f'<div class="stat-number" style="color:{color};">{count}</div>'
            f'<div class="stat-label">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    for ticket in tickets:
        assessment = ticket.get("assessment", {})
        lead = ticket.get("lead", {})
        products = ticket.get("products", {})
        temp = assessment.get("temperature", "cold")
        temp_label = {"hot": "🔥 ساخن", "warm": "💡 دافئ", "cold": "🧊 بارد"}.get(temp, temp)
        temp_class = f"temp-{temp}"
        ticket_id = ticket.get("ticket_id", "N/A")
        summary = ticket.get("conversation_summary", "")
        action = ticket.get("recommended_action", "")
        timestamp = ticket.get("timestamp", "")

        st.markdown(
            f'<div class="ticket-card">'
            f'<div class="ticket-header">'
            f'<span class="ticket-id">{ticket_id}</span>'
            f'<div><span class="ticket-temp {temp_class}">{temp_label}</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        cols = st.columns([1, 1])

        with cols[0]:
            st.markdown('<div class="ticket-section">', unsafe_allow_html=True)
            st.markdown('<div class="ticket-section-title">👤  معلومات العميل — Lead Info</div>', unsafe_allow_html=True)
            _render_field("الاسم — Name", lead.get("name", "—"))
            _render_field("رقم الهاتف — Phone", lead.get("phone", "—"))
            _render_field("البريد — Email", lead.get("email", "—"))
            _render_field("المدينة — City", lead.get("city", "—"))
            _render_field("اللغة — Language", lead.get("language", "—"))
            _render_field("اللهجة — Dialect", lead.get("dialect", "—"))
            _render_field("قناة التواصل — Channel", lead.get("contact_channel", "—"))
            st.markdown('</div>', unsafe_allow_html=True)

        with cols[1]:
            st.markdown('<div class="ticket-section">', unsafe_allow_html=True)
            st.markdown('<div class="ticket-section-title">🎯  الاهتمامات — Interests</div>', unsafe_allow_html=True)
            courses = products.get("courses", [])
            tracks = products.get("tracks", [])
            diplomas = products.get("diplomas", [])
            _render_field("كورسات — Courses", "، ".join(courses) if courses else "—")
            _render_field("مسارات — Tracks", "، ".join(tracks) if tracks else "—")
            _render_field("دبلومات — Diplomas", "، ".join(diplomas) if diplomas else "—")
            _render_field("الهدف — Goal", products.get("goal", "—"))
            _render_field("المستوى — Level", products.get("current_level", "—"))
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="ticket-section">', unsafe_allow_html=True)
        st.markdown('<div class="ticket-section-title">📊  التقييم — Assessment</div>', unsafe_allow_html=True)
        signals = assessment.get("buying_signals", [])
        if signals:
            signals_html = "".join(f'<span class="signal-badge">{s}</span>' for s in signals)
            st.markdown(f'<div class="ticket-field"><span class="ticket-label">إشارات شراء — Signals: </span><br>{signals_html}</div>', unsafe_allow_html=True)
        objections = assessment.get("objections", [])
        if objections:
            _render_field("اعتراضات — Objections", "، ".join(objections))
        _render_field("حساسية السعر — Budget", assessment.get("budget_sensitivity", "—"))
        st.markdown('</div>', unsafe_allow_html=True)

        if summary:
            is_ar = any("\u0600" <= c <= "\u06FF" for c in summary)
            st.markdown(
                f'<div class="ticket-section">'
                f'<div class="ticket-section-title">💬  ملخّص المحادثة — Conversation Summary</div>'
                f'<div class="summary-text {"arabic-ar" if is_ar else "arabic-en"}">'
                f'{summary}</div></div>',
                unsafe_allow_html=True,
            )

        if action:
            is_ar = any("\u0600" <= c <= "\u06FF" for c in action)
            st.markdown(
                f'<div class="ticket-section">'
                f'<div class="ticket-section-title">📌  الإجراء التالي — Next Action</div>'
                f'<div class="summary-text {"arabic-ar" if is_ar else "arabic-en"}">'
                f'{action}</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            f'<div style="text-align:left;font-size:0.8rem;color:#6B7A8F;margin-top:0.5rem;">'
            f'{timestamp}</div>',
            unsafe_allow_html=True,
        )

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def _render_field(label: str, value: str):
    if value and value != "—":
        st.markdown(
            f'<div class="ticket-field">'
            f'<span class="ticket-label">{label}: </span>'
            f'<span class="ticket-value">{value}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
