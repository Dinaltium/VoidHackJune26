# Deployment Guide: Hosting Agent Defender

To demonstrate the **Agent Defender** live to judges and record your walkthrough video, we recommend hosting the stack online. 

Here is the recommended blueprint: **Vercel** for the Next.js Dashboard and **Render** for the Python/FastAPI Backend.

---

## 1. Hosting the Backend (FastAPI Proxy) on Render

Render's free tier is ideal for the Python FastAPI server because it supports persistent web sockets and Server-Sent Events (SSE), allowing the live defender decision feed to stream in real-time.

### Step-by-Step Render Deployment:
1. Log in to [Render](https://render.com) and click **New > Web Service**.
2. Connect your GitHub repository: `Dinaltium/VoidHackJune26`.
3. Configure the Web Service settings:
   - **Name**: `defender-backend`
   - **Language**: `Python 3`
   - **Build Command**: `pip install -r proxy/requirements.txt`
   - **Start Command**: `python -m uvicorn app.main:app --app-dir proxy --host 0.0.0.0 --port 10000`
4. Add **Environment Variables**:
   - `GROQ_API_KEY`: Set this to your Groq API key (`gsk_...`) so model-backed safeguards work out of the box.
   - `CORS_ORIGINS`: Set this to your Vercel frontend URL (once deployed, e.g., `https://voidhack-dashboard.vercel.app`) to allow the browser to safely query the APIs.
5. Click **Deploy Web Service**. Render will build and deploy the container.

> [!NOTE]
> Render's free tier spins down after 15 minutes of inactivity. When you demonstrate it, open the backend URL first (e.g. `https://your-service.onrender.com/health`) to trigger a cold-start wakeup (takes ~50 seconds).

---

## 2. Hosting the Frontend (Next.js) on Vercel

Vercel is the native platform for Next.js, handling automatic builds, static optimizations, and edge routing.

### Step-by-Step Vercel Deployment:
1. Log in to [Vercel](https://vercel.com) and click **Add New > Project**.
2. Import your GitHub repository: `Dinaltium/VoidHackJune26`.
3. In the configure project screen:
   - **Root Directory**: Select `dashboard` (crucial, since the Next.js app sits inside the `dashboard/` subfolder).
   - **Framework Preset**: `Next.js` (automatically detected).
4. Expand **Environment Variables** and add:
   - `NEXT_PUBLIC_API_URL`: Set this to your Render backend URL (e.g., `https://defender-backend.onrender.com`).
5. Click **Deploy**. Vercel will build and launch your dashboard.

---

## 3. Alternative: Hugging Face Spaces (Backend)

If you prefer to host the backend on Hugging Face Spaces (Docker-based space):
1. Create a new Space on [Hugging Face](https://huggingface.co/spaces) and choose **Docker** SDK.
2. In your repo, add a `Dockerfile` inside the root or proxy directory targeting the FastAPI server.
3. Configure Space secrets to store the `GROQ_API_KEY`.
4. *Trade-off*: Hugging Face proxy servers sometimes buffer SSE output streams or impose strict iframe CORS restrictions, making Render a simpler, more robust choice for standard dashboard integration.
