# Streamlit Cloud Setup Guide

This guide explains how to set up your Kayf AI Sales Agent on Streamlit Cloud with proper secrets.

## What Secrets Are Required?

The app needs the following secrets to function properly:

| Secret Name | Purpose | Example | How to Get |
|-------------|---------|---------|-----------|
| `MONGO_URI` | MongoDB database connection | `mongodb+srv://user:pass@cluster.mongodb.net/?appName=Kayfa` | Create free MongoDB Atlas account |
| `OPENROUTER_API_KEY` | LLM API for chat responses | `sk-or-v1-...` | Get from [openrouter.ai](https://openrouter.ai) |
| `LOGIN_USERNAME` | CRM lon username | `admin` | Set to any value you prefer |
| `LOGIN_PASSWORD` | CRM login password | `secure_password_123` | Set to a secure value |

**Without these secrets, the app will:**
- Not be able to connect to the database
- Respond with fallback messages instead of using the AI
- Not save lead information to CRM

---

## Step 1: Deploy to Streamlit Cloud

1. Push your code to GitHub (if not already done):
   ```bash
   git push origin main
   ```

2. Go to [share.streamlit.io](https://share.streamlit.io)

3. Click **"Create app"** → **"From existing repo"**

4. Fill in:
   - **Repository**: `USIF-Andreas226/Task3`
   - **Branch**: `main`
   - **Main file path**: `app.py`

5. Click **Deploy**

---

## Step 2: Add Secrets in Streamlit Cloud

Once your app is deployed:

1. In the Streamlit Cloud app dashboard, click the **⋮** (three dots) menu in the top-right
2. Select **Settings**
3. Scroll to **Secrets**
4. Paste the following template in the **Secrets** editor (in TOML format):

```toml
# MongoDB connection
MONGO_URI = "mongodb+srv://your_username:your_password@kayfa.np3dv8l.mongodb.net/?appName=Kayfa"
MONGO_DB = "kayfa_crm"
MONGO_COLLECTION = "tickets"

# OpenRouter API (REQUIRED for chat to work!)
OPENROUTER_API_KEY = "sk-or-v1-your-actual-api-key-here"
OPENROUTER_MODEL = "openai/gpt-oss-20b:free"

# App login credentials
LOGIN_USERNAME = "admin"
LOGIN_PASSWORD = "your_secure_password_here"
```

---

## Step 3: Get Your OpenRouter API Key

**This is the most important step** — without it, the app will only respond with fallback messages!

1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up for a free account
3. Click on your **Profile** → **API Keys**
4. Create a new API key (or copy your existing one)
5. Copy the key (starts with `sk-or-v1-`)
6. Paste it into the Streamlit Cloud secrets as shown above

**Note:** The free tier has limited requests. If you hit the limit, you'll need to upgrade or wait for the quota reset.

---

## Step 4: Get Your MongoDB Connection String

If you don't have a MongoDB database yet:

1. Go to [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. Sign up for a free account
3. Create a new **Cluster** (free tier available)
4. Create a **Database User** (e.g., username: `kayfa_user`, password: your_password)
5. Click **Connect** → **Drivers** → **Python**
6. Copy the connection string
7. Replace `<username>` and `<password>` with your credentials
8. Paste it into Streamlit Cloud secrets

If you already have a connection string from before, use that.

---

## Step 5: Redeploy and Test

1. After adding secrets, Streamlit Cloud will automatically redeploy
2. Wait for the deployment to complete (green checkmark)
3. Visit your app URL and test:
   - Type a message in the chat
   - You should get an AI response (not just the fallback greeting)
   - Try: "Tell me about AI courses" or "دورات الذكاء الاصطناعي"

---

## Troubleshooting

### App Always Shows Fallback Messages

**This means:** `OPENROUTER_API_KEY` is not set correctly or the API call is failing.

**Fix:**
1. Go back to **Settings** → **Secrets**
2. Verify `OPENROUTER_API_KEY` starts with `sk-or-v1-`
3. Check that there are no extra spaces or quotes around the key
4. Redeploy by making a small commit:
   ```bash
   git commit --allow-empty -m "Trigger redeploy"
   git push origin main
   ```

### "Connection refused" or MongoDB errors

**This means:** `MONGO_URI` is incorrect or your IP is not whitelisted.

**Fix:**
1. Go to MongoDB Atlas
2. Click **Network Access**
3. Click **Add IP Address**
4. Select **Allow access from anywhere** (or add Streamlit Cloud's IP)
5. Update `MONGO_URI` in Streamlit Cloud secrets if needed

### "Invalid credentials" on login

**This means:** `LOGIN_USERNAME` or `LOGIN_PASSWORD` don't match.

**Fix:**
1. Update secrets with correct credentials
2. Redeploy

---

## Checking Logs for Errors

If you need to debug:

1. In Streamlit Cloud, click the app name
2. Click **View logs** (bottom right)
3. Look for error messages related to:
   - `OPENROUTER_API_KEY`
   - `MONGO_URI`
   - `OpenAI` or API errors

---

## Security Best Practices

✅ **DO:**
- Use environment variables and Streamlit Secrets (never hardcode in code)
- Use strong, unique passwords for MongoDB and app login
- Rotate your OpenRouter API key regularly if needed
- Keep your repo public (secrets are NOT in the code)

❌ **DON'T:**
- Commit `.env` files with real secrets to GitHub
- Share API keys in chat or emails
- Use the same password across multiple services
- Use weak passwords like "password123"

---

## Example Working Configuration

Here's what a properly configured secrets file looks like (with placeholder values):

```toml
MONGO_URI = "mongodb+srv://kayfa_user:my_secure_password@cluster.mongodb.net/?appName=Kayfa"
MONGO_DB = "kayfa_crm"
MONGO_COLLECTION = "tickets"
OPENROUTER_API_KEY = "sk-or-v1-abcd1234efgh5678ijkl9012mnop3456"
OPENROUTER_MODEL = "openai/gpt-oss-20b:free"
LOGIN_USERNAME = "admin"
LOGIN_PASSWORD = "my_secure_crm_password"
```

---

## Still Not Working?

1. **Check that the app deployed successfully** — You should see a green checkmark next to your app
2. **Wait 1-2 minutes** — Streamlit Cloud may need time to restart with new secrets
3. **Check the logs** — Look for specific error messages
4. **Test locally first** — Run `streamlit run app.py` locally with proper `.env` file to verify it works
5. **Contact support** — If nothing works, visit [streamlit.io/community](https://discuss.streamlit.io)

---

## Alternative: Self-Hosted Deployment

If Streamlit Cloud doesn't work for you, consider:

- **Railway** — [railway.app](https://railway.app) — Similar setup to Streamlit Cloud
- **Render** — [render.com](https://render.com) — Free tier available
- **Docker** — Run locally or on any VPS with Docker
- **Your own server** — Full control, but requires more setup

See [DEPLOYMENT.md](DEPLOYMENT.md) for more options.
