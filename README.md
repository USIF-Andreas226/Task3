# Week 3 Task — Agentic AI Internship @ Kayfa: AI Sales Agent

An intelligent AI Sales Agent for Kayfa — a conversational assistant that understands what visitors want, recommends the right Kayfa products grounded in the real catalog, handles objections honestly, moves conversations toward enrollment, and captures leads as CRM tickets.

## 🚀 Features

- **Bilingual Chat** — Speaks Arabic (Egyptian, Saudi, Syrian dialects) and English with automatic language detection
- **RAG-Grounded Responses** — All answers are grounded in Kayfa's real knowledge base (52 courses, 13 roadmaps, pricing, policies, diploma briefs)
- **Intent Detection** — Identifies browsing, comparing, price-sensitive, hesitant, and ready-to-enroll visitors
- **Lead Capture** — Detects buying signals, collects prospect info, and saves rich CRM tickets to MongoDB (with in-memory fallback)
- **Persuasive Sales** — Handles objections (price, time, experience, trust) with pre-written responses from diploma briefs
- **RTL Support** — Correct right-to-left rendering for Arabic text throughout the UI

## 🏗 Architecture

```
├── app.py                          # Streamlit entry point with page navigation
├── pages/
│   ├── chat_agent.py               # Chat interface page
│   └── crm_tickets.py              # CRM ticket viewer page
├── src/
│   ├── agent.py                    # Sales Agent logic (intent, dialect, lead capture)
│   ├── rag.py                      # Knowledge Base & RAG retrieval
│   └── crm.py                      # MongoDB CRM integration with Pydantic models
├── data/
│   ├── kayfa_courses.json          # 52 structured courses
│   ├── kayfa_roadmaps.json         # 13 learning paths (10 tracks + 3 live diplomas)
│   ├── kayfa_company_overview.md   # Company identity, accreditation, team
│   ├── kayfa_policies_faqs.md      # Refund policy, payment, certificates, FAQs
│   ├── kayfa_privacy_policy.md     # Data protection and privacy
│   ├── kayfa_instructors.md        # 25 instructor profiles
│   ├── kayfa_paid_individual_courses.md  # Paid course catalog with prices
│   ├── kayfa_paid_educational_tracks.md  # Self-paced track details
│   ├── kayfa_free_educational_content.md # Free courses and resources
│   ├── diploma_ai.md              # AI Diploma sales brief
│   ├── diploma_data_science.md    # Data Science Diploma sales brief
│   ├── diploma_soc.md             # SOC Diploma sales brief
│   ├── diploma_pen_test.md        # Penetration Testing Diploma sales brief
│   ├── diploma_full_stack.md      # Full-Stack Diploma sales brief
│   └── data_summary.md            # Data reference guide
├── requirements.txt
└── .streamlit/config.toml
```

## 🛠 Setup

```bash
# Install dependencies
pip install -r requirements.txt

# (Optional) Set MongoDB URI for persistent CRM storage
export MONGO_URI="mongodb://your-mongo-instance:27017"

# Run the app
streamlit run app.py
```

The app runs without MongoDB — it falls back to in-memory storage automatically.

## 🔧 Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB` | `kayfa_crm` | Database name |
| `MONGO_COLLECTION` | `tickets` | Collection name |

## 📋 Pages

1. **Chat Agent** (`/`) — Conversational AI that visitors interact with. Quick topic buttons, chat history, RTL support.
2. **CRM Tickets** (`/crm`) — Dashboard showing all captured leads with temperature, contact info, interests, conversation summary, and recommended next action.

## 🤖 Agent Capabilities

- **Intent & Dialect Detection**: Automatically identifies visitor intent and Arabic dialect
- **Course Recommendations**: Maps visitor goals to real Kayfa products
- **Objection Handling**: Addresses concerns about price, timing, prerequisites, trust, and refunds
- **Lead Scoring**: Hot/Warm/Cold based on buying signals and engagement
- **CRM Ticket Creation**: Captures name, phone, city, products of interest, buying signals, objections, and conversation summary in Arabic

## 🧪 Testing

```bash
python3 -c "
from src.rag import KnowledgeBase
from src.crm import CRMClient
from src.agent import SalesAgent

kb = KnowledgeBase()
crm = CRMClient()
agent = SalesAgent(kb, crm)

response = agent.generate_response('أنا مهتم بتعلم الأمن السيبراني')
print(response)

response = agent.generate_response('I want to enroll in the AI diploma')
print(response)
"
```
