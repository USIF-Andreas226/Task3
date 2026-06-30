# Task Tracking

## Week 2 Detailed Plan

### Completed
- ✅ Decouple `chat_agent.py` from environment with default config
- ✅ Add `crm.py` secrets to .streamlit/secrets.toml for local use
- ✅ Replace APScheduler with daily trigger for Streamlit Cloud
- ✅ Add "🗑️ Clear All CRM Tickets" button
- ✅ Delete all tickets from MongoDB in `delete_all_tickets()`
- ✅ Filter Arabic verbs ("هختار"/"اختار") from name extraction
- ✅ Add twilio>=8.0.0 to requirements.txt
- ✅ Convert monitoring_trace.py conversation_id to strings and filter NaN
- ✅ Add user_map email mapping and get_user_conversations() method to crm.py
- ✅ Daily report trigger at 8:00-8:05 AM
- ✅ Get user's conversations from messages (not just usage logs)
- ✅ Admin "Test WhatsApp Report Now" button and crm.py test_report function
- ✅ Detailed error logging for WhatsApp init failures
- ✅ Use os.environ["KEY"] in whatsapp.py (now inside __init__)
- ✅ Keep local secrets in .streamlit/secrets.toml (not committed)

### In Progress
- 🔄 Debug why using `selected_user` "yousefmalak123456@gmail.com" returns no conversations despite having 7 usage logs

#### Current Issue
- User created new account with "yousefmalak123456@gmail.com"
- Has 7 usage logs with user_id matching the account
- get_user_conversations(user_id) returns []
- usage logs' conversation_id column contains only NaN/"nan" values

#### Root Cause Hypothesis
Usage logs created WITHOUT a conversation_id. Need to check save_message and log_usage_entry functions.

### Remaining Work
- Fix conversation_id in usage logs (add tracking field)
- If logs missing conversation_id, query MongoDB messages directly by user_id
- Show onboarding flow for new user conversations if needed