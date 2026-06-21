# Deployment Guide — Environment Variables & Secrets

## Local Development

The app automatically loads environment variables from:
1. `.env` — local development file (gitignored)
2. `.env.local` — optional local overrides (gitignored)

### Quick Start Locally

1. Create or update `.env` file with your credentials:
   ```env
   MONGO_URI=mongodb+srv://your_username:your_password@kayfa.np3dv8l.mongodb.net/?appName=Kayfa
   OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here
   LOGIN_USERNAME=admin
   LOGIN_PASSWORD=your_secure_password
   ```

2. Run locally:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

---

## Deployment Platforms

### Streamlit Cloud

1. Push your code to GitHub (secrets are already removed and in `.gitignore`)
2. Go to [Streamlit Cloud Dashboard](https://share.streamlit.io)
3. Click **"New app"** → connect your GitHub repo
4. Once deployed, go to **Settings** → **Secrets**
5. Add your environment variables in TOML format:

   ```toml
   MONGO_URI = "mongodb+srv://username:password@kayfa.np3dv8l.mongodb.net/?appName=Kayfa"
   OPENROUTER_API_KEY = "sk-or-v1-your-actual-key-here"
   LOGIN_USERNAME = "admin"
   LOGIN_PASSWORD = "your_secure_password"
   ```

6. Redeploy the app after adding secrets.

### Docker / Self-Hosted

1. Set environment variables in your `.env` file or via Docker:

   ```bash
   docker run -e MONGO_URI="..." -e OPENROUTER_API_KEY="..." -p 8501:8501 kayfa-app
   ```

   Or use a `.env` file:
   ```bash
   docker run --env-file .env -p 8501:8501 kayfa-app
   ```

2. Or modify `docker-compose.yml`:
   ```yaml
   environment:
     - MONGO_URI=${MONGO_URI}
     - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
     - LOGIN_USERNAME=${LOGIN_USERNAME}
     - LOGIN_PASSWORD=${LOGIN_PASSWORD}
   ```

### Railway, Render, Heroku

1. In your platform's dashboard, go to **Environment Variables** or **Secrets**
2. Add each variable:
   - `MONGO_URI`
   - `OPENROUTER_API_KEY`
   - `LOGIN_USERNAME`
   - `LOGIN_PASSWORD`

3. Redeploy or restart the app.

---

## Environment Variables Reference

| Variable | Purpose | Example |
|----------|---------|---------|
| `MONGO_URI` | MongoDB connection string | `mongodb+srv://user:pass@cluster.mongodb.net/?appName=Kayfa` |
| `OPENROUTER_API_KEY` | OpenRouter API key for LLM | `sk-or-v1-...` |
| `LOGIN_USERNAME` | CRM login username | `admin` |
| `LOGIN_PASSWORD` | CRM login password | (set to secure value in production) |

---

## Security Best Practices

✅ **DO:**
- Store secrets in your deployment platform's secret management (Streamlit Secrets, Docker Secrets, etc.)
- Use `.env.example` as a template for developers
- Keep `.env` and `.env.local` in `.gitignore`
- Rotate credentials regularly

❌ **DON'T:**
- Commit `.env` files with real secrets to Git
- Share API keys in code or chat
- Use the same credentials in development and production
- Use weak passwords for login credentials

---

## Troubleshooting

### App won't load / "ModuleNotFoundError"
- Ensure `requirements.txt` is up-to-date
- Run `pip install -r requirements.txt` locally
- Check that all imports are available

### "Invalid credentials" on login
- Verify `LOGIN_USERNAME` and `LOGIN_PASSWORD` are set correctly
- Check Streamlit Secrets (if deployed) match your expected values
- Ensure `.env` file exists and is readable locally

### MongoDB connection fails
- Verify `MONGO_URI` is correct
- Check MongoDB IP whitelist includes your deployment server's IP
- Ensure the connection string has proper authentication

### API calls fail / OpenRouter errors
- Verify `OPENROUTER_API_KEY` is correct and has remaining quota
- Check that the API key has not expired
- Ensure your OpenRouter account is active
