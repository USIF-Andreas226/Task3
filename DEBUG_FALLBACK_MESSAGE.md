# Debugging: Why App Still Shows Fallback Messages

## Checklist

### 1. Did you add secrets to Streamlit Cloud? (Not local .env)

❌ **DON'T DO THIS:**
- Just update your local `.env` file
- Push to GitHub
- That won't work! Streamlit Cloud doesn't read `.env` files

✅ **DO THIS:**
- Go to: https://share.streamlit.io
- Click your app name (Task3)
- Click **⋮** (three dots) → **Settings**
- Click **Secrets**
- Paste your credentials there
- Click **Save**

### 2. Verify Credentials Format

Your secrets should look like this in Streamlit Cloud (exactly this format):

```toml
MONGO_URI = "mongodb+srv://USERNAME:PASSWORD@cluster.mongodb.net/?appName=Kayfa"
MONGO_DB = "kayfa_crm"
MONGO_COLLECTION = "tickets"
OPENROUTER_API_KEY = "REPLACE_WITH_YOUR_OPENROUTER_API_KEY"
OPENROUTER_MODEL = "openai/gpt-oss-20b:free"
LOGIN_USERNAME = "admin"
LOGIN_PASSWORD = "your_password_here"
```

**Important:** No `[mongo]` or `[OPENROUTER_API]` section headers in Streamlit Cloud!
Use the flat format above.

### 3. Wait for Redeployment

After adding secrets:
1. Streamlit Cloud automatically redeploys
2. Wait 30-60 seconds for deployment to complete
3. You should see a green checkmark next to your app
4. Hard refresh browser: **Ctrl+F5** (Windows) or **Cmd+Shift+R** (Mac)

### 4. Check App Logs for Errors

1. In Streamlit Cloud, click your app
2. Click **View logs** (bottom right corner)
3. Look for errors like:
   - `❌ OPENROUTER_API_KEY is not set`
   - `❌ Connection refused to MongoDB`
   - `API Error: ...`

If you see `✓ LLM client initialized successfully` → API key is working

### 5. Test Locally First

Before relying on Streamlit Cloud, test locally:

1. Update local `.env` with real credentials:
   ```env
   MONGO_URI=mongodb+srv://USERNAME:PASSWORD@cluster.mongodb.net/?appName=Kayfa
   OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY_HERE
   ```

2. Run test script:
   ```bash
   python3 test_api.py
   ```

3. Expected output:
   ```
   ✅ SUCCESS! API is working!
      Response: OpenRouter API is working!
   ```

4. If that works, run app:
   ```bash
   streamlit run app.py
   ```

5. Type in chat — should see AI responses now!

---

## If Still Not Working

### Problem: "API key is still a placeholder"

**Solution:**
- API key format must start with `sk-or-v1-` followed by exactly 64 characters
- Copy-paste from openrouter.ai (don't type manually)
- No spaces, no truncation

### Problem: "MongoDB connection refused"

**Solution:**
- MongoDB might be down or IP not whitelisted
- In MongoDB Atlas → **Network Access** → allow your IP
- Or use: **Allow access from anywhere** (less secure but works)

### Problem: "Still seeing fallback message after all this"

**Solution:**
1. Make sure you're testing AFTER redeployment (wait 60 seconds)
2. Hard refresh browser (Ctrl+F5)
3. Clear browser cache
4. Try a different browser
5. Check app logs for actual error messages

---

## Complete Verification Workflow

```
1. Update Streamlit Cloud Secrets
   ↓
2. Wait 30-60 seconds for redeployment
   ↓
3. Hard refresh browser (Ctrl+F5)
   ↓
4. Check app logs for errors
   ↓
5. Type a test message in chat
   ↓
6. Should see AI response (NOT fallback)
```

---

## Expected Behavior Changes

### ❌ Before (Fallback Message)
- User types: "دورات الذكاء الاصطناعي"
- App responds: "شكراً لاهتمامك في كايفة! 😊..."
- Status: API not connected

### ✅ After (Real AI Response)
- User types: "دورات الذكاء الاصطناعي"  
- App responds: "إليك 5 دورات في الذكاء الاصطناعي: 1) Introduction to AI... 2) Deep Learning with TensorFlow..."
- Status: API connected and working

---

## Need Help?

If it's still not working after this:

1. Share the output of:
   ```bash
   python3 test_api.py
   ```

2. Share app logs from Streamlit Cloud (View logs → bottom right)

3. Confirm:
   - [ ] Credentials added to Streamlit Cloud Secrets (not just local)
   - [ ] Waited 60 seconds for redeployment
   - [ ] Hard refreshed browser
   - [ ] API key format is correct (sk-or-v1-...)
   - [ ] MongoDB connection string is correct
