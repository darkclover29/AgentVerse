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

## 2. Deploying the React Frontend (Vercel)

Vercel is optimized for React static hosting and automatically configures builds.

### Steps:
1. Sign up/Log in to [Vercel](https://vercel.com/).
2. Click **Add New** and select **Project**.
3. Import your GitHub repository.
4. Configure the project:
   - **Root Directory**: `frontend` *(Crucial: This tells Vercel to compile the code inside the `/frontend` folder)*
   - **Framework Preset**: `Vite` (should auto-detect)
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Under **Environment Variables**, add:
   - **Key**: `VITE_API_BASE_URL`
   - **Value**: `https://your-backend.onrender.com` *(Replace with your actual Render URL)*
6. Click **Deploy**.

Vercel will build your static files and deploy them to a custom `.vercel.app` domain (or your own custom domain).

---

## 3. How the Dual-Mode Connection Works

To keep local development frictionless without mutating codebase files, we use an environment-aware API check inside [api.js](frontend/src/api.js):
- **Development**: In local development, the `VITE_API_BASE_URL` variable is omitted, so it defaults to relative paths (`/api` and `/ws`), which Vite proxies to `http://localhost:8000`.
- **Production**: When built on Vercel with `VITE_API_BASE_URL` configured, Vite compiles the hosted backend URL directly into the production code. 
- **WebSocket Protocol**: The frontend automatically extracts the hostname from the API URL and switches between secure `wss://` (production) and standard `ws://` (local) protocols.
- **Static Fallback**: If the Render backend is sleeping or offline, the API layer automatically pings `/api/health`, fails, and falls back to **Static Replay Mode** by folding the pre-recorded 30-day run in [replay_data.json](frontend/public/replay_data.json) entirely client-side.
