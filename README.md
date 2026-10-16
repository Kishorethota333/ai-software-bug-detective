# AI Software Bug Detective

AI-assisted bug triage MVP using React/Vite, FastAPI, SQLAlchemy, JWT, and an optional OpenAI/Groq provider. It includes login, projects, bugs, safe log uploads, AI diagnosis, suggested fixes, test-case generation, and a dashboard.

## Requirements
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ for shared/dev deployment (SQLite works out of the box for a quick local smoke test)
- Optional: OpenAI or Groq API key for live AI responses

## 1. Backend setup (Windows PowerShell)
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env. For the quickest local start, keep DATABASE_URL=sqlite:///./bug_detective.db
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs. The app creates tables on startup for this MVP.

## 2. Frontend setup (new terminal)
```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```
Open the Vite URL shown in terminal (normally http://localhost:5173).

## 3. First login
Register a user using the Register link on the login page. The first user should be treated as the initial administrator for a demo; this MVP assigns `ADMIN` to the first registered user and `DEVELOPER` to subsequent registrations. In a real deployment, disable public registration or require an administrator invitation.

## PostgreSQL setup
Create a database named `bug_detective`, then set e.g.:
`DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/bug_detective`
The PostgreSQL driver is included. This MVP stores relational data in PostgreSQL; pgvector/RAG tables are an extension point and are not required for the core workflow.

## AI provider
- `AI_PROVIDER=mock` works without an API key and returns a clearly labeled heuristic diagnosis.
- For OpenAI set `AI_PROVIDER=openai`, `AI_API_KEY=...`, and optionally `AI_MODEL=gpt-4o-mini`.
- For Groq set `AI_PROVIDER=groq`, `AI_API_KEY=...`, and optionally `AI_MODEL=llama-3.3-70b-versatile`.
Never commit `.env` or real keys. AI outputs are suggestions; review before applying fixes.

## Included MVP workflow
Login → Create Project → Create Bug → Attach LOG/TXT/JSON/PY/JS/JSX/SQL/PDF/PNG/JPG file → Analyze → review root cause, confidence, fix and generated test cases.

## Checks
Backend tests: `pytest` from `backend/`. Frontend production build: `npm run build` from `frontend/`.

## Production checklist
Use a strong unique `JWT_SECRET`, PostgreSQL, HTTPS, private file storage, managed secrets, backups, rate limiting, audit logging, restricted CORS, malware scanning, and controlled registration. This starter is not a claim of production certification. Validate integrations and security for your environment before deployment.
