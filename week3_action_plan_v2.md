# Week 3 Graduation Project — Action Plan (Updated)
**Phase 1 ✅ DONE — Phase 2 + 3 remaining**

---

## ✅ Phase 1 — Status: Complete

Already built in the current codebase:

| Component | File | Status |
|---|---|---|
| Streamlit multi-page app + CSS/RTL | `app.py` | ✅ |
| Sales agent (intent, dialect, lead capture) | `src/agent.py` | ✅ |
| RAG retrieval (TF-IDF + fuzzy, no LLM) | `src/rag.py` | ✅ |
| CRM Pydantic models + MongoDB client | `src/crm.py` | ✅ |
| Chat UI with RTL bubbles | `pages/chat_agent.py` | ✅ |
| CRM tickets dashboard (admin) | `pages/crm_tickets.py` | ✅ |
| Knowledge base (52 courses, 13 roadmaps, 10 md files) | `data/` | ✅ |
| Auth (login/password from env/secrets) | `app.py L149-189` | ✅ |

> ⚠️ **One gap to patch before moving on**: current auth is a single shared `admin/test123` credential — there's no per-user sign-up or `user_id`. Phase 2 monitoring is built on `user_id` per message, so this needs to be fixed **first** as part of Phase 2 setup.

---

## 🔧 Phase 2 — Monitoring, Cost & Optimization

### Step 1 — Patch Auth → Real User Accounts *(prerequisite for all of Phase 2)*

The current login is one shared account. Phase 2 needs every message tied to an identified `user_id`.

**Add to MongoDB: `users` collection**
```python
{
  "_id": ObjectId,
  "user_id": str,          # uuid or email-based
  "email": str,
  "password_hash": str,    # bcrypt
  "role": "user" | "admin",
  "created_at": datetime
}
```

**Changes to `app.py`:**
- [ ] Replace the hardcoded `LOGIN_USERNAME/PASSWORD` block (L149-189) with a real sign-up/login form
- [ ] Sign-up: email + password → hash with `bcrypt` → insert into `users` collection
- [ ] Login: email + password → verify hash → store `user_id` + `role` in `st.session_state`
- [ ] Role guard: `admin` sees CRM + monitoring pages; `user` sees chat only
- [ ] Pass `st.session_state.user_id` into every `generate_response()` call

**Changes to `src/agent.py`:**
- [ ] `generate_response()` (L434): accept `user_id` + `conversation_id` as params
- [ ] Stamp both on every MongoDB write (messages + CRM tickets already have ticket schema, messages need a new collection)

**New collection: `messages`**
```python
{
  "message_id": str,
  "user_id": str,
  "conversation_id": str,
  "role": "user" | "assistant",
  "content": str,
  "timestamp": datetime
}
```

---

### Step 2 — `usage_logs` Collection (Cost + Trace data source)

Every call to OpenRouter in `_llm_response()` (L641-691) must write one log record **after** it completes.

**Add to `src/crm.py` or a new `src/usage_logger.py`:**

```python
{
  "log_id": str,
  "user_id": str,
  "conversation_id": str,
  "message_id": str,            # links to messages collection
  "model": str,                 # e.g. "openai/gpt-4o-mini"
  "provider": str,              # "OpenRouter"
  "input_tokens": int,
  "output_tokens": int,
  "embedding_tokens": int,      # 0 if not applicable (rag.py uses no LLM)
  "llm_cost_usd": float,
  "embedding_cost_usd": float,  # 0 for now (pure Python RAG)
  "total_cost_usd": float,
  "tool_calls": [               # list of RAG calls made this turn
    {
      "tool_name": str,         # "search_kb", "get_roadmap"
      "args": dict,
      "result_summary": str,    # first 200 chars of result
      "sources": list[str],     # file names returned
      "latency_ms": int
    }
  ],
  "think_step": str,            # reasoning note (build manually — see below)
  "final_response": str,
  "latency_ms": int,            # total round-trip
  "timestamp": datetime
}
```

**Changes to `src/agent.py` — `_llm_response()` (L641-691):**
- [ ] Record `start = time.time()` before OpenRouter call
- [ ] After response: extract `usage.prompt_tokens`, `usage.completion_tokens` from the API response object
- [ ] Calculate cost: `llm_cost = (prompt_tokens * IN_RATE + completion_tokens * OUT_RATE) / 1_000_000`
- [ ] Store pricing constants per model in a `PRICING` dict at the top of the file
- [ ] Collect which RAG tools were called this turn (pass them in from `generate_response`)
- [ ] Build a `think_step` string: short note of what intent/signals were detected before calling LLM
- [ ] Call `usage_logger.log(...)` with all of the above

> **Note on embeddings**: `rag.py` uses pure Python TF-IDF/fuzzy — no embedding API calls, so `embedding_tokens = 0` and `embedding_cost_usd = 0.00` for now. Document this clearly in the dashboard.

---

### Step 3 — Cost Monitor Dashboard

**New file: `pages/monitoring_cost.py`**

Admin-only page. Reads from `usage_logs` collection.

#### UI Sections:

**A) Summary Cards (top row)**
```
Total Spend    Conversations    Messages    Avg Cost/Conv
  $0.0483           12             87          $0.0040
```

**B) Per-Message Table**
- Columns: Timestamp | User | Model | Input tokens | Output tokens | Cost | Latency
- Sort by cost descending to surface expensive replies
- Filter by: date range, user

**C) Per-Conversation Rollup**
- Group `usage_logs` by `conversation_id`
- Show: conversation_id (shortened), user, message count, total tokens, total cost
- Click to drill into individual message costs

**D) Per-User Rollup**
- Group by `user_id`
- Show: email, conversation count, total messages, total cost
- Answers "who is costing the most?"

**E) Provider Breakdown**
- Since `rag.py` has no embedding cost right now, show:
  - LLM cost (OpenRouter) = total
  - Embedding cost = $0.00 (note: pure Python retrieval)
  - Combined total

---

### Step 4 — Behaviour & Response Trace Dashboard

**New file: `pages/monitoring_trace.py`**

Admin-only page. Reads from `usage_logs` (same collection, different view).

#### UI Flow:
1. **Select User** → dropdown of all users
2. **Select Conversation** → list of that user's conversations
3. **Select Message/Prompt** → list of user prompts in that conversation
4. **Trace Replay** → expand the full step-by-step:

```
┌─────────────────────────────────────────┐
│ 🧠 THINK                                │
│ Intent: ready_to_enroll                 │
│ Signals: ['price', 'enrollment']        │
│ Dialect: Egyptian                       │
│ Plan: retrieve SOC diploma details      │
├─────────────────────────────────────────┤
│ 🔧 TOOL CALL 1: search_kb               │
│ args: {query: "SOC diploma price", k:5} │
├─────────────────────────────────────────┤
│ 📦 TOOL RESULT 1                        │
│ sources: kayfa_soc_diploma.md           │
│          kayfa_paid_educational_tracks  │
│ chunks: 4 returned                      │
│ latency: 12ms                           │
├─────────────────────────────────────────┤
│ 💬 FINAL RESPONSE                       │
│ دبلومة الـ SOC مناسبة تمامًا...         │
├─────────────────────────────────────────┤
│ 📊 METADATA                             │
│ tokens: 2,140 in · 380 out              │
│ cost: $0.000375  latency: 2.8s          │
└─────────────────────────────────────────┘
```

**Hallucination flag logic:**
- [ ] If final response contains a price/course name AND no `tool_calls` with matching source → show 🚨 **"No retrieval found for this claim"**
- [ ] Specifically check for `$` amounts and course names appearing without a prior `search_kb` call

---

### Step 5 — Optimization Write-up

From the trace data, find and fix one wasteful pattern. Most likely candidates given the current codebase:

**Candidate A — System prompt size per turn**
- `SYSTEM_PROMPT_AR` is ~2,000 tokens, re-sent every single turn
- Fix: trim to ~800 tokens, move static catalog info into RAG context only when needed
- Measure: token count before vs after on 5 identical conversations

**Candidate B — RAG context over-retrieval**
- `retrieve_context()` in `rag.py` always fetches tracks summary + top 5 courses + roadmaps + diploma docs
- For simple greetings or off-topic questions, this sends ~1,500 unnecessary tokens
- Fix: add an intent gate — only fetch diploma docs if `intent == "ready_to_enroll"` or diploma keyword detected
- Measure: average input tokens for greetings before vs after

**Candidate C — Fallback path redundancy**
- `_fallback_response()` (L693-727) is called when OpenRouter fails, but still runs full detection pipeline
- Low-impact but easy to document

**What to submit:**
- [ ] Screenshot/table of the wasteful pattern from the monitor
- [ ] Code diff of the fix
- [ ] Before vs after: avg input tokens + avg cost per message (run same 5 test prompts both ways)

---

## 🗂️ Updated File Structure After Phase 2

```
app.py                          # updated: real auth, user_id in session
src/
  agent.py                      # updated: user_id param, usage logging, think_step
  rag.py                        # no changes needed
  crm.py                        # updated: users collection, messages collection
  usage_logger.py               # NEW: write usage_logs records
  pricing.py                    # NEW: model pricing constants
pages/
  chat_agent.py                 # minor: pass user_id to agent
  crm_tickets.py                # no changes needed
  monitoring_cost.py            # NEW
  monitoring_trace.py           # NEW
```

---

## ✅ Phase 3 — Deployment & Submission

### Repo Cleanup
- [ ] Repo name: `Week 3 Task — Agentic AI Internship @ Kayfa: AI Sales Agent`
- [ ] `.gitignore`: exclude `.env`, `.env.local`, `__pycache__`
- [ ] `requirements.txt`: add `bcrypt` for password hashing
- [ ] `README.md`: local setup steps, env vars table, live link, demo video link

### Streamlit Cloud
- [ ] All secrets in `.streamlit/secrets.toml`: `OPENROUTER_API_KEY`, `MONGO_URI`
- [ ] Remove hardcoded `admin/test123` fallback before deploying
- [ ] Test full flow on live deploy: sign-up → chat → lead captured → admin login → monitoring

### Demo Video (cover both parts)
- [ ] **Part 1**: sign-up as user → Arabic chat (try Egyptian dialect) → buying signals trigger → CRM ticket appears in admin view
- [ ] **Part 2**: admin login → cost monitor (per-message, per-user) → trace viewer (pick one message, show full replay) → show the optimization before/after numbers
- [ ] Show RTL Arabic clearly in at least one screen

---

## 📋 Final Submission Checklist

- [ ] Sign-up/login works with real user accounts (not hardcoded)
- [ ] Every message/ticket stamped with `user_id` + `conversation_id`
- [ ] `usage_logs` written after every OpenRouter call
- [ ] Cost monitor: per-message, per-conversation, per-user — correct totals
- [ ] Trace monitor: think → tool call (args) → result (sources) → final answer → cost per step
- [ ] Hallucination flag working (no retrieval = 🚨)
- [ ] One optimization: wasteful pattern identified + fix applied + before/after numbers shown
- [ ] Live deploy is login-protected
- [ ] Repo clean, README complete
- [ ] Demo video covers both parts
