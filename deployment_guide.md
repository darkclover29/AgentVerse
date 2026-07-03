# AgentVerse Deployment Guide

This guide explains how to deploy **AgentVerse** to production using free-tier cloud hosting.

- **Backend**: Python FastAPI hosted on **Render** (or Railway / Fly.io) in fallback mode (zero-cost, heuristic planning rules when Ollama is offline).
- **Frontend**: Vite + React hosted on **Vercel** (or Netlify / GitHub Pages).

---

## 1. Deploying the FastAPI Backend (Render)

Render is a great free-tier hosting platform that automatically detects and deploys Python Web Services.

### Steps:
1. Sign up/Log in to [Render](https://render.com/).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub repository.
4. Configure the Web Service:
   - **Name**: `agentverse-backend` (or similar)
   - **Language**: `Python`
   - **Root Directory**: `backend` *(Crucial: This tells Render to run commands inside the `/backend` folder where `requirements.txt` and `app/` reside)*
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Click **Create Web Service**.

Once active, Render will give you a public URL (e.g., `https://agentverse-backend.onrender.com`). Note this URL down for the frontend step.

*Note: Free-tier Render instances go to sleep after 15 minutes of inactivity. When a new user hits the site, it will auto-wake (which takes ~50 seconds to boot up).*

---

## 2. Deploying the React Frontend (Cloudflare Pages or Vercel)

Both Cloudflare Pages and Vercel are excellent free static hosting platforms.

### Option A: Cloudflare Pages (Recommended)
1. Sign up/Log in to the [Cloudflare Dashboard](https://dash.cloudflare.com/).
2. Navigate to **Workers & Pages** and click **Create** -> **Pages** -> **Connect to Git**.
3. Select your GitHub repository.
4. Set up the build settings:
   - **Project Name**: `agentverse` (or similar)
   - **Production Branch**: `main`
   - **Framework Preset**: `None` (or configure manually)
   - **Root Directory**: `frontend` *(Tells Cloudflare to compile code inside `/frontend`)*
   - **Build Command**: `npm run build`
   - **Build Output Directory**: `dist`
5. Click **Save and Deploy**. Cloudflare will run the initial build.
6. Configure the backend URL variable:
   - Once deployed, go to the project's **Settings** -> **Environment Variables**.
   - Click **Add Variable** under *Production* (and optionally *Preview*).
   - Set **Variable Name**: `VITE_API_BASE_URL`
   - Set **Value**: `https://your-backend.onrender.com` *(Replace with your Render URL)*
   - Save the settings.
7. Go to **Deployments** -> select the latest deployment -> click **Retry Deployment** (or trigger a new git push) so it builds with the environment variable active.

### Option B: Vercel
1. Sign up/Log in to [Vercel](https://vercel.com/).
2. Click **Add New** and select **Project**.
3. Import your GitHub repository.
4. Configure the project settings:
   - **Root Directory**: `frontend` *(Crucial: compiles the code inside the `/frontend` folder)*
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Expand **Environment Variables** and add:
   - **Key**: `VITE_API_BASE_URL`
   - **Value**: `https://your-backend.onrender.com`
6. Click **Deploy**.

---

## 3. How the Dual-Mode Connection Works

To keep local development frictionless without mutating codebase files, we use an environment-aware API check inside [api.js](frontend/src/api.js):
- **Development**: In local development, the `VITE_API_BASE_URL` variable is omitted, so it defaults to relative paths (`/api` and `/ws`), which Vite proxies to `http://localhost:8000`.
- **Production**: When built on Vercel with `VITE_API_BASE_URL` configured, Vite compiles the hosted backend URL directly into the production code. 
- **WebSocket Protocol**: The frontend automatically extracts the hostname from the API URL and switches between secure `wss://` (production) and standard `ws://` (local) protocols.
- **Static Fallback**: If the Render backend is sleeping or offline, the API layer automatically pings `/api/health`, fails, and falls back to **Static Replay Mode** by folding the pre-recorded 30-day run in [replay_data.json](frontend/public/replay_data.json) entirely client-side.
