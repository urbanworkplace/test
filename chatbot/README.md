little baby — Chatbot

This folder contains a static frontend (`templates/chat.html`) and a Python Flask backend (`server.py`) that can run locally or be deployed.

Recommended deployment
- Frontend: Vercel (static)
- Backend: Render or Railway (Python service)

Vercel frontend (static)
1. Ensure `vercel.json` exists at repository root (it does).
2. Update `chatbot/templates/chat.html` meta tag `backend-url` to point to your deployed backend URL (e.g., https://my-backend.onrender.com).
3. Deploy the project on Vercel (select this repository). Vercel will serve static files from `chatbot/templates`.

Backend (Render)
1. Create a new service on Render (or Railway) using the repository.
2. Set the start command to: `python server.py` and the working directory to `chatbot`.
3. Add environment variables in Render:
   - `GRAQ_API_KEY` = <your key>
   - `GRAQ_API_URL` = <graq endpoint>
4. Deploy.

Local testing
1. Create virtualenv and install dependencies:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3 -m pip install -r chatbot\requirements.txt
```

2. Run backend:
```powershell
py -3 chatbot\server.py
```

3. Open `chatbot/templates/chat.html` in browser or visit `http://127.0.0.1:5000` when backend is running and `backend-url` meta points to `http://127.0.0.1:5000`.

Notes
- Do NOT store secrets in the frontend. The `GRAQ_API_KEY` must be set on the backend service only.
- If you want serverless APIs on Vercel instead of a separate backend, tell me and I can convert endpoints into Vercel Serverless Functions (Python or Node.js).
  
Vercel serverless backend (optional)
1. This repository now includes Node.js serverless functions under `api/` (routes at `/api/*`). These provide `POST /api/chat`, `POST /api/create_chat`, `GET /api/chats`, `GET /api/chat/:id` and `GET /api/ping`.
2. IMPORTANT: Vercel serverless functions are ephemeral — they do not provide reliable persistent disk storage. The included functions use in-memory storage per server instance. For real persistent memory use Vercel KV, a database, or host the Python backend elsewhere (Render/Railway).
3. To deploy on Vercel:
   - Add the repo to Vercel.
   - Set project Environment Variables (in Vercel dashboard): `GRAQ_API_KEY` and, optionally, `GRAQ_API_URL` and `GRAQ_MODEL`.
   - Deploy. The frontend will be served from `chatbot/templates` and serverless APIs from `/api/*`.

Local testing with serverless API (optional):
1. Install dependencies (Node >=18 recommended). If you need `uuid` or `node-fetch` locally, run:

```bash
npm init -y
npm install uuid node-fetch
```

2. Run Vercel CLI locally (optional):

```bash
npm i -g vercel
vercel dev
```

This will serve both the frontend and the `/api` endpoints locally.