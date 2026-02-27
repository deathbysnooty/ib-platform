# IB Past Papers Platform — Setup Guide

This guide walks you through every step from zero to a running platform.
Estimated time: ~45 minutes on first setup.

---

## Overview of what you need

| Thing | Purpose |
|---|---|
| Google Cloud project | Lets us use the Drive API and Google login |
| Service account | Reads files from your Drive on behalf of the app |
| OAuth 2.0 Client ID | Lets students sign in with their Google account |
| Anthropic API key | Powers the AI chat and paper summaries |

---

## Step 1 — Google Cloud project

1. Go to [https://console.cloud.google.com](https://console.cloud.google.com)
2. Click **Select a project → New Project**
3. Name it `ib-platform` and click **Create**
4. Make sure it's selected in the top bar

---   

## Step 2 — Enable the Google Drive API

1. In the Cloud Console, go to **APIs & Services → Library**
2. Search for **Google Drive API** and click **Enable**

---

## Step 3 — Authorise Drive access

> **If you see "Service account key creation is disabled"** — your Google Workspace
> organisation blocks service account JSON keys. Use **Method A** below instead.

---

### Method A — OAuth refresh token ✅ (works even when keys are blocked)

This lets the app access Drive using *your* Google account, authorised once.

**3a.** First complete Step 4 below to get your OAuth Client ID and Secret,
then come back here.

**3b.** Run the token generator script:

```bash
cd ib-platform/backend
source .venv/bin/activate
python get_refresh_token.py
```

It will ask for your Client ID and Secret, open a browser for you to sign in
to the Google account that owns the Drive folder, then print three lines:

```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...
```

Paste all three into your `backend/.env`.

**3c.** Copy the Drive folder ID:

Open your root IB Past Papers folder in Drive. Copy the ID from the URL:
`https://drive.google.com/drive/folders/`**`1AbCdEfGhIjKlMnOpQrStUvWxYz`**

Paste it as `DRIVE_ROOT_FOLDER_ID` in `.env`.

---

### Method B — Service account JSON (only if key creation is allowed)

1. Go to **APIs & Services → Credentials**
2. Click **+ CREATE CREDENTIALS → Service account**
3. Name: `ib-platform-drive`, click **Create and Continue**, then **Done**
4. Click the service account email → **Keys** tab → **Add Key → Create new key → JSON**
5. A `.json` file downloads — paste its entire contents as `GOOGLE_SERVICE_ACCOUNT_JSON` in `.env`
6. Share your Drive folder with the service account email (role: Viewer)
7. Copy the folder ID as `DRIVE_ROOT_FOLDER_ID` (same as Method A step 3c)

---

## Step 4 — Create OAuth 2.0 credentials (for student Google login)

1. Go to **APIs & Services → Credentials**
2. Click **+ CREATE CREDENTIALS → OAuth client ID**
3. If prompted, configure the **OAuth consent screen** first:
   - User type: **External**
   - App name: `IB Past Papers`
   - Add your email as a test user
4. Back in Create OAuth client ID:
   - Application type: **Web application**
   - Name: `IB Platform`
   - Authorised JavaScript origins:
     - `http://localhost:5173` (for local dev)
     - `https://your-production-domain.com` (add later)
   - Authorised redirect URIs: *(leave blank — we use the popup flow)*
5. Click **Create** — copy the **Client ID** (ends in `.apps.googleusercontent.com`)

---

## Step 5 — Get an Anthropic API key

1. Sign up / log in at [https://console.anthropic.com](https://console.anthropic.com)
2. Go to **API Keys → Create Key**
3. Copy the key (starts with `sk-ant-`)

---

## Step 6 — Set up the backend

```bash
cd ib-platform/backend

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create your .env file
cp .env.example .env
```

Open `backend/.env` and fill in every value:

```env
DRIVE_ROOT_FOLDER_ID=<paste folder ID from Step 3>

# Paste the ENTIRE contents of the service account JSON file as one line:
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}

ANTHROPIC_API_KEY=sk-ant-...

GOOGLE_CLIENT_ID=<paste from Step 4>

# Generate a random secret:  openssl rand -hex 32
JWT_SECRET=<random 64-char hex string>

FRONTEND_URL=http://localhost:5173

# Comma-separated email domains your students use, e.g.:
ALLOWED_EMAIL_DOMAINS=gmail.com
# Or leave blank to allow all Google accounts

ADMIN_EMAIL=you@example.com

ENV=development
```

> **Tip for the service account JSON**: open the downloaded `.json` file in a
> text editor, select all, copy, and paste it on one line in `.env`.
> Make sure you escape any quotes if needed, or use a tool like:
> `python3 -c "import json,sys; print(json.dumps(json.load(open('key.json'))))" >> .env`

### Start the backend

```bash
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO  Building Drive index …
INFO  Index complete — 243 files indexed.
INFO  Application ready.
```

---

## Step 7 — Set up the frontend

```bash
cd ib-platform/frontend

# Install dependencies (requires Node.js 18+)
npm install

# Create your .env file
cp .env.example .env
```

Open `frontend/.env` and fill in:

```env
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=<same Client ID from Step 4>
```

### Start the frontend

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) — you should see the sign-in page.

---

## Step 8 — Test it

1. Sign in with your Google account
2. Try: **"Math AA HL May 2024"** — you should see paper cards appear
3. Click **Download** to get the PDF
4. Click **AI Summary** to see the question-by-question breakdown

---

## Refreshing the paper index

When you add new papers to Google Drive, run:

```bash
curl -X POST http://localhost:8000/api/admin/refresh-index \
  -H "Cookie: session=<your session cookie>"
```

Or just restart the backend — it re-indexes on startup.

---

## Deploying to production

### Backend → Railway (free tier)

1. Push the `backend/` folder to a GitHub repo
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add all your `.env` variables in Railway's **Variables** tab
4. Set `ENV=production` and `FRONTEND_URL=https://your-vercel-app.vercel.app`

### Frontend → Vercel (free tier)

1. Push the `frontend/` folder to GitHub
2. Go to [vercel.com](https://vercel.com) → New Project → import the repo
3. Set environment variables:
   - `VITE_API_URL` = your Railway backend URL
   - `VITE_GOOGLE_CLIENT_ID` = your OAuth client ID
4. In Google Cloud Console, add your Vercel URL to **Authorised JavaScript origins**

---

## File naming reference

Your Drive files are parsed automatically. The parser understands:

| Pattern | Extracted |
|---|---|
| Folder `2025 May Math AA HL` | year=2025, session=May, subject=Math AA, level=HL |
| Folder `2024 November Physics HL` | year=2024, session=November, subject=Physics, level=HL |
| File `Mathematics_analysis_paper_2__TZ1_HL.pdf` | paper=2, timezone=TZ1, type=question |
| File `...paper_1_TZ2_SL_markscheme.pdf` | paper=1, timezone=TZ2, type=markscheme |
| File `...TZ1_HL_MS.pdf` | timezone=TZ1, type=markscheme |

If a file isn't showing up, check that:
- The folder name includes the year (e.g. `2024`) and session (`May` / `November`)
- The file name contains `TZ1`, `TZ2`, or `TZ3`
- The file is a `.pdf`

---

## Project structure

```
ib-platform/
├── backend/
│   ├── main.py          # FastAPI app & routes
│   ├── drive.py         # Google Drive indexing & file access
│   ├── chat.py          # Claude API (query parsing + summarization)
│   ├── auth.py          # Google OAuth & JWT sessions
│   ├── models.py        # Pydantic data models
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.tsx
    │   ├── api.ts          # API client
    │   ├── types.ts        # TypeScript types
    │   └── components/
    │       ├── LoginPage.tsx
    │       ├── ChatPage.tsx
    │       ├── MessageBubble.tsx
    │       ├── PaperCard.tsx    # Download + AI Summary cards
    │       └── SummaryModal.tsx
    ├── package.json
    └── .env.example
```
