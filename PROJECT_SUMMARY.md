# Project Summary: Kayf AI Sales Agent

## Architecture Overview
```
app.py (Entry Point) 
├── pages/chat_agent.py (Chat UI)
├── pages/crm_tickets.py (CRM Dashboard)
└── src/
    ├── agent.py (Sales Logic: Intent, Dialect, Lead Capture)
    ├── rag.py (Knowledge Base & RAG Retrieval)
    └── crm.py (MongoDB + Pydantic Models)
```

---

## Core Files

### app.py — Streamlit Entry Point & Navigation
- **Lines 19-24**: Page config (title "Kayf — AI Sales Agent", wide layout)
- **Lines 29-128**: Custom CSS with Cairo/Inter fonts, dark theme, RTL support
- **Lines 133-147**: Session state navigation between "chat" and "crm" pages
- **Lines 149-154**: Login credentials from env/secrets (default: admin/test123)
- **Lines 156-189**: Protected CRM page with login form
- **Lines 191-196**: Dynamic page loading via `st.session_state.page`

### src/agent.py — Sales Agent Core Logic (796 lines)
| Component | Lines | Purpose |
|-----------|-------|---------|
| **LLM Client** | 16-39 | OpenRouter client with validation, lazy init |
| **Pattern Constants** | 42-113 | Regex for buying signals, timing, cold signals, objections, intents |
| **System Prompts** | 116-228 | Arabic (SYSTEM_PROMPT_AR) & English (SYSTEM_PROMPT_EN) with strict rules |
| **SalesAgent Class** | 231-796 | Main agent logic |

**Key Methods:**
- `detect_language()` (244-246): Arabic char ratio > 30% → "ar"
- `detect_dialect()` (248-258): Egyptian/Saudi/Syrian keyword matching
- `detect_intent()` (260-276): Scores patterns → browsing/comparing/price_sensitive/hesitant/ready_to_enroll
- `detect_buying_signals()` (278-294): 9 signal types (enrollment, price, installment, timing, discount, cert, contact, ready, phone)
- `detect_objections()` (296-302): price/time/experience/trust/refund/comparison
- `detect_timing()` (320-330): now/week/month/later classification
- `get_temperature()` (339-360): hot/warm/cold based on signals + intent
- `extract_lead_info()` (362-424): Name, phone (11-digit 01xxxxxxxxx), email, city extraction
- `generate_response()` (434-571): Main pipeline — detects → tracks → LLM → captures lead
- `_track_products()` (573-639): Scans conversation for course/track/diploma mentions
- `_llm_response()` (641-691): Builds prompt with RAG context, calls OpenRouter
- `_fallback_response()` (693-727): Graceful degradation when LLM unavailable
- `_generate_summary()` (770-796): Arabic/English conversation summary for CRM

### src/rag.py — Knowledge Base & Retrieval (372 lines)
| Class | Lines | Purpose |
|-------|-------|---------|
| **KnowledgeBase** | 35-248 | Loads JSON/Markdown, provides search methods |
| **RAGRetriever** | 250-371 | Assembles context for LLM |

**KnowledgeBase Methods:**
- `search_courses()` (59-89): Filter by query, track, level, price, paid/free
- `search_roadmaps()` (100-130): Semantic + fuzzy matching on skills/name
- `semantic_search_courses()` (175-197): Expanded query with AR/EN mapping + fuzzy scoring
- `get_recommendations()` (199-247): Goal→track mapping, level/budget filtering
- `AR_EN_MAP` (8-30): 22 bilingual keyword mappings (فول ستاك→full stack, ذكاء اصطناعي→ai, etc.)

**RAGRetriever.retrieve_context() (254-371):**
1. Always includes available tracks summary
2. Top 5 semantic course matches with price/duration
3. Relevant roadmaps (self-paced + live diplomas) with course names
4. Fallback: all courses in detected track if <2 matches
5. Diploma markdown docs (diploma_ai.md, diploma_soc.md, etc.)
6. Refund policy from kayfa_policies_faqs.md
7. General markdown search fallback
8. Company overview if context still sparse

### src/crm.py — CRM Models & Storage (224 lines)
**Pydantic Models:**
- `LeadInfo` (24-56): name, phone (regex ^01\d{9}$), email, city, language, dialect, channel, time
- `ProductsOfInterest` (59-83): courses[], tracks[], diplomas[], goal, level, prerequisites
- `LeadAssessment` (86-113): temperature (cold/warm/hot), buying_signals[], budget_sensitivity, objections[], intent
- `CRMTicket` (116-152): lead + products + assessment + summary + action + timestamp + ticket_id (LEAD-2026-XXXX)

**CRMClient** (154-224):
- MongoDB Atlas with 5s timeout, falls back to in-memory list
- `save_ticket()` (178-195): Generates sequential ticket_id, persists to MongoDB + memory
- `get_all_tickets()` (197-214): Merges MongoDB + memory, deduplicates by ticket_id

---

## Page Files

### pages/chat_agent.py (158 lines)
- `initialize_session()` (7-12): Creates KnowledgeBase, CRMClient, SalesAgent once per session
- `show()` (17-97): Chat UI with greeting banner, message history, streaming input
- `_quick_topic()` (82-88): Quick buttons (Web Dev, AI/ML, Cybersecurity, Data Science)
- `_render_bubble()` (90-97): RTL/LTR bubbles based on Arabic char detection
- `_render_css()` (100-157): Chat-specific styling (fixed input, gradients, RTL)

### pages/crm_tickets.py (211 lines)
- `show()` (5-200): Dashboard with stats grid (hot/warm/cold/total) + ticket cards
- Ticket cards show: lead info, interests (courses/tracks/diplomas), assessment (signals/objections/budget), conversation summary, recommended action, timestamp
- RTL for Arabic, LTR for English summaries
- Refresh button (74-75)

---

## Data Files (in `/data/`)
| File | Format | Records | Key Fields |
|------|--------|---------|------------|
| `kayfa_courses.json` | JSON | 52 | id, name, summary, track, level, duration, prerequisites, price, paid, roadmaps[] |
| `kayfa_roadmaps.json` | JSON | 13 | 10 self-paced tracks (R001-R010) + 3 live diplomas (R011-R013), skills, tools, course_ids[], price |
| `kayfa_company_overview.md` | Markdown | - | Mission, accreditation, team, contacts |
| `kayfa_policies_faqs.md` | Markdown | - | Refund, payment, certificates, FAQs |
| `kayfa_privacy_policy.md` | Markdown | - | Data protection |
| `kayfa_instructors.md` | Markdown | 25 | Bios, certifications, dialects |
| `kayfa_paid_individual_courses.md` | Markdown | - | Priced course catalog |
| `kayfa_paid_educational_tracks.md` | Markdown | - | Track details with installments |
| `kayfa_free_educational_content.md` | Markdown | 6 free | Entry-level courses |
| `diploma_*.md` (5 files) | Markdown | - | Sales briefs with objection handling |

---

## Configuration
- **requirements.txt**: streamlit, pydantic[email], pymongo, python-dotenv, openai
- **.env.example** / **.env.local**: OPENROUTER_API_KEY, MONGO_URI, LOGIN_USERNAME, LOGIN_PASSWORD
- **.streamlit/config.toml**: Streamlit config
- **.streamlit/secrets.toml**: Cloud secrets template

---

## Key Design Decisions
1. **No LLM for retrieval** — Pure Python semantic/fuzzy search in `rag.py`, LLM only for generation
2. **Bilingual first-class** — Arabic dialects detected, RTL rendering, prompts in both languages
3. **Lead capture flow** — Name + phone required before pricing, timing question gates temperature
4. **Graceful degradation** — In-memory CRM fallback, fallback responses when OpenRouter unavailable
5. **Strict grounding** — System prompts forbid hallucination; "not in knowledge base" responses

---

## Deployment
- **Local**: `streamlit run app.py` (auto-loads .env, .env.local)
- **Streamlit Cloud**: Push to GitHub, add secrets in dashboard (see STREAMLIT_CLOUD.md)
