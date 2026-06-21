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

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables in `.env` file (see .env.example)
# Or export them:
export OPENROUTER_API_KEY="sk-or-v1-your-key"
export MONGO_URI="mongodb://your-mongo-instance:27017"
export LOGIN_USERNAME="admin"
export LOGIN_PASSWORD="your_password"

# Run the app
streamlit run app.py
```

The app runs without MongoDB — it falls back to in-memory storage automatically.

### 🌐 Deploy to Streamlit Cloud

For full deployment instructions, see **[STREAMLIT_CLOUD.md](STREAMLIT_CLOUD.md)** ← **Start here!**

Quick summary:
1. Push code to GitHub
2. Deploy via [share.streamlit.io](https://share.streamlit.io)
3. Add secrets in Streamlit Cloud settings (see [STREAMLIT_CLOUD.md](STREAMLIT_CLOUD.md) for template)
4. **Required secrets**: `OPENROUTER_API_KEY`, `MONGO_URI`, `LOGIN_USERNAME`, `LOGIN_PASSWORD`

## 🔧 Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB` | `kayfa_crm` | Database name |
| `MONGO_COLLECTION` | `tickets` | Collection name |

---

## 🔑 Required APIs & Services

This app requires the following external APIs and services to function properly. **Without them, the app will use fallback responses.**

### 1. OpenRouter API (Required for LLM Chat)

**Purpose:** Provides the LLM intelligence for the chat agent to generate personalized responses.

**Why it's required:** Without this, the chat will only show generic fallback messages instead of AI-powered recommendations.

#### Setup Steps:

1. Go to [openrouter.ai](https://openrouter.ai)
2. Click **Sign Up** (free account available)
3. Complete registration and email verification
4. Navigate to **Profile** → **API Keys**
5. Click **Create New API Key**
6. Copy the key (format: `sk-or-v1-...`)
7. Add to your environment:
   ```bash
   export OPENROUTER_API_KEY="sk-or-v1-your-key-here"
   ```
   Or in Streamlit Cloud → **Settings** → **Secrets**:
   ```toml
   OPENROUTER_API_KEY = "sk-or-v1-your-key-here"
   ```

#### API Details:

| Property | Value |
|----------|-------|
| **Base URL** | `https://openrouter.ai/api/v1` |
| **Default Model** | `openai/gpt-oss-20b:free` |
| **Auth Method** | Bearer token in header |
| **Free Tier** | Limited requests/month (check your account) |
| **Rate Limit** | Depends on subscription |
| **Pricing** | Free tier available; pay-as-you-go after quota |

#### Example Usage (Internal):

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="sk-or-v1-your-key-here",
    default_headers={
        "HTTP-Referer": "https://kayfa.com",
        "X-Title": "Kayfa AI Sales Agent",
    },
)

response = client.chat.completions.create(
    model="openai/gpt-oss-20b:free",
    messages=[
        {"role": "system", "content": "You are a sales assistant..."},
        {"role": "user", "content": "Tell me about AI courses"}
    ],
    temperature=0.7,
    max_tokens=600,
)
print(response.choices[0].message.content)
```

**Status Check:** If you see this in logs: `✓ LLM client initialized successfully` → API is working
If you see this: `❌ OPENROUTER_API_KEY is not set` → API key is missing

---

### 2. MongoDB Atlas (Optional but Recommended)

**Purpose:** Persistent database to store lead information, CRM tickets, conversation history.

**Why it's optional:** The app falls back to in-memory storage if MongoDB is unavailable. Data persists only during the session.

**Why it's recommended for production:** Saves all leads, enables team collaboration, preserves history.

#### Setup Steps:

1. Go to [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. Click **Sign Up** (free tier available: 512MB storage)
3. Create a **New Project** → **New Cluster**
4. Choose **M0 (Free)** tier
5. Wait for cluster to deploy (5-10 minutes)
6. Click **Connect** → **Drivers** → **Python 3.6+**
7. Copy the connection string:
   ```
   mongodb+srv://<username>:<password>@cluster.mongodb.net/?appName=Kayfa
   ```
8. In **Security** → **Database Access**, create a username/password
9. Replace `<username>` and `<password>` in the connection string
10. Add to environment:
    ```bash
    export MONGO_URI="mongodb+srv://username:password@cluster.mongodb.net/?appName=Kayfa"
    ```
    Or in Streamlit Cloud → **Settings** → **Secrets**:
    ```toml
    MONGO_URI = "mongodb+srv://username:password@cluster.mongodb.net/?appName=Kayfa"
    MONGO_DB = "kayfa_crm"
    MONGO_COLLECTION = "tickets"
    ```

#### API Details:

| Property | Value |
|----------|-------|
| **Service** | MongoDB Atlas (Cloud MongoDB) |
| **Protocol** | MongoDB Wire Protocol over TLS |
| **Free Tier** | 512MB storage, shared cluster |
| **Paid Tier** | Starting $57/month for dedicated cluster |
| **Drivers** | Python PyMongo (included in requirements.txt) |
| **Data Stored** | Lead info, CRM tickets, conversation history |

#### Example Usage (Internal):

```python
from pymongo import MongoClient

client = MongoClient("mongodb+srv://user:pass@cluster.mongodb.net/?appName=Kayfa")
db = client["kayfa_crm"]
tickets_collection = db["tickets"]

# Store a lead
ticket = {
    "lead_name": "أحمد",
    "phone": "0791234567",
    "email": "ahmad@example.com",
    "temperature": "hot",
    "buying_signals": ["طلب تسجيل", "سؤال عن السعر"],
    "created_at": datetime.utcnow()
}
result = tickets_collection.insert_one(ticket)
print(f"Ticket ID: {result.inserted_id}")

# Retrieve all tickets
all_tickets = list(tickets_collection.find())
for ticket in all_tickets:
    print(f"Lead: {ticket['lead_name']}, Temperature: {ticket['temperature']}")
```

**Status Check:** If MongoDB is connected, leads are saved to the database. If not connected, logs show: `⚠️ MongoDB not available, using in-memory storage`

---

### 3. Streamlit Cloud (Optional Hosting)

**Purpose:** Free hosting platform for deploying the Streamlit app online.

**Why it's optional:** You can run locally or on any other hosting platform.

**Why it's recommended for production:** Free, automatic deployments from GitHub, easy secret management.

#### Setup Steps:

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **Create app** → **From existing repo**
4. Select your GitHub repository
5. Deploy
6. Add secrets (see [STREAMLIT_CLOUD.md](STREAMLIT_CLOUD.md))

#### Supported Features:

| Feature | Support |
|---------|---------|
| **Deployments** | Automatic from GitHub |
| **Secrets Management** | Via Settings → Secrets panel |
| **Custom Domain** | Paid plan only |
| **Storage** | Up to 1GB per app |
| **Compute** | Shared cloud resources |
| **Pricing** | Free tier available |

---

## 📡 API Integration Summary

```
┌─────────────────────────────────────┐
│   Streamlit App (Frontend)          │
├─────────────────────────────────────┤
│ app.py → pages/ → src/              │
│   ├─ src/agent.py (Sales Logic)    │
│   ├─ src/rag.py (Knowledge Base)   │
│   └─ src/crm.py (Lead Storage)     │
└─────────────────────────────────────┘
         ↓            ↓            ↓
    ┌────────────────────────────────┐
    │ OpenRouter API (LLM)           │
    │ https://openrouter.ai/api/v1   │
    └────────────────────────────────┘
         ↓            ↓
    ┌────────────────────────────────┐
    │ MongoDB Atlas (Database)       │
    │ mongodb+srv://...              │
    └────────────────────────────────┘
```

---

## ✅ Checklist Before Production

- [ ] OpenRouter API key obtained and configured
- [ ] MongoDB Atlas cluster created (optional but recommended)
- [ ] Environment variables set locally or in Streamlit Cloud
- [ ] All secrets added to `.gitignore` (check git status)
- [ ] Tested chat locally with real API key
- [ ] Tested lead capture and CRM storage
- [ ] Deployed to Streamlit Cloud or your own server
- [ ] Verified app works online
- [ ] Set up team access for CRM dashboard
- [ ] Trained team on usage

---

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
