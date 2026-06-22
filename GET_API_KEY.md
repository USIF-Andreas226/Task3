# Complete Guide: Getting & Setting Real Secrets for Streamlit Cloud

## The Problem

Your current secrets have:
```toml
OPENROUTER_API_KEY = "sk-or-v1-local-test-key-replace-this-with-real-key"
```

This is a **placeholder**, not a real API key. OpenRouter rejects it, so the app only shows fallback messages.

---

## Solution: Get a Real OpenRouter API Key (3 minutes)

### Step 1: Sign Up at OpenRouter

1. Go to **https://openrouter.ai**
2. Click **Sign Up** (top right)
3. Enter your email address
4. Create a password
5. Check your email for verification link
6. Click the verification link
7. You're signed in!

### Step 2: Create/Get Your API Key

1. Click your **Profile** (top-right corner)
2. Click **API Keys** (left sidebar)
3. You should see a default API key, OR click **Create New Key**
4. Copy the full key (it starts with `sk-or-v1-`)
5. Keep this key safe (treat it like a password)

**Example of a real key:**
```
sk-or-v1-abc123def456ghi789jkl012mno345pqr
```

---

## Step 3: Update Streamlit Cloud Secrets

### If Deploying to Streamlit Cloud:

1. Go to **https://share.streamlit.io**
2. Find your deployed app (Task3)
3. Click the **⋮** (three dots) menu
4. Click **Settings**
5. Scroll to **Secrets**
6. Paste this (replace YOUR_REAL_KEY):

```toml
# MongoDB configuration
MONGO_URI = "mongodb+srv://local_user:local_pass@localhost/?appName=Kayfa_Dev"
MONGO_DB = "kayfa_crm"
MONGO_COLLECTION = "tickets"

# OpenRouter API (REPLACE sk-or-v1-... with your REAL key!)
OPENROUTER_API_KEY = "sk-or-v1-YOUR-REAL-KEY-FROM-OPENROUTER-HERE"
OPENROUTER_MODEL = "openai/gpt-oss-20b:free"

# App login credentials
LOGIN_USERNAME = "admin"
LOGIN_PASSWORD = "test123"
```

7. Click **Save**
8. Streamlit Cloud will redeploy automatically (wait 30-60 seconds)
9. Test your app!

---

## Step 4: Update Local .env (For Testing)

If you want to test locally first:

1. Get your real API key from openrouter.ai
2. Update `.env` file:

```env
# MongoDB Atlas connection string
MONGO_URI=mongodb+srv://local_user:local_pass@localhost/?appName=Kayfa_Dev
MONGO_DB=kayfa_crm
MONGO_COLLECTION=tickets

# OpenRouter API key (REPLACE WITH YOUR REAL KEY!)
OPENROUTER_API_KEY=sk-or-v1-YOUR-REAL-KEY-HERE
OPENROUTER_MODEL=openai/gpt-oss-20b:free

# App login credentials
LOGIN_USERNAME=admin
LOGIN_PASSWORD=test123
```

3. Save the file
4. Run locally:
   ```bash
   streamlit run app.py
   ```
5. Test the chat - now you should see AI responses!

---

## Step 5: Verify It Works

Run this test script to confirm your API key works:

```bash
python3 test_api.py
```

Expected output if successful:
```
✅ SUCCESS! API is working!
   Response: OpenRouter API is working!
```

---

## Before/After Comparison

### ❌ BEFORE (Placeholder Key)
```toml
OPENROUTER_API_KEY = "sk-or-v1-local-test-key-replace-this-with-real-key"
```

User types: "Tell me about AI courses"
Response: "شكراً لاهتمامك في كايفة! 😊 أقدر أساعدك..."
(Generic fallback only)

### ✅ AFTER (Real Key)
```toml
OPENROUTER_API_KEY = "sk-or-v1-abc123def456ghi789jkl012mno345pqr"
```

User types: "Tell me about AI courses"
Response: "Here are 5 AI courses: [1] Introduction to AI & Prompt Engineering... [2] Deep Learning with TensorFlow... [detailed recommendations with prices]"
(AI-powered personalized response)

---

## Common Mistakes

❌ **Don't:**
- Use the placeholder key and deploy
- Share your API key with others
- Commit real API keys to Git (they're in .gitignore, so shouldn't happen)
- Use the same key across multiple apps if concerned about quota

✅ **Do:**
- Get a new key from openrouter.ai
- Use the full key starting with `sk-or-v1-`
- Keep the key in Streamlit Cloud Secrets (not in code)
- Monitor your API usage at https://openrouter.ai/account/usage

---

## Troubleshooting

### "Still seeing fallback messages after updating secrets"

1. Check you copied the FULL API key (no spaces, no truncation)
2. Wait 1-2 minutes for Streamlit Cloud to redeploy
3. Hard refresh your browser (Ctrl+F5 or Cmd+Shift+R)
4. Run test script: `python3 test_api.py`

### "API key validation error"

1. Go back to openrouter.ai → Profile → API Keys
2. Verify your key is active and not revoked
3. Copy and paste again (don't type it manually)
4. Check you have remaining API quota

### "Free tier quota exceeded"

1. Check usage at: https://openrouter.ai/account/usage
2. Wait for quota to reset (usually monthly)
3. Or upgrade to paid plan
4. Or use a different LLM provider

---

## Next Steps

1. ✅ Get real API key from openrouter.ai
2. ✅ Update Streamlit Cloud secrets OR local .env
3. ✅ Redeploy/restart
4. ✅ Test with `python3 test_api.py`
5. ✅ Type a message in the chat
6. ✅ Verify you get AI responses (not fallback messages)

**That's it!** Your app will now work properly with real AI responses.
