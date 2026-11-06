# AI Software Bug Detective

AI-assisted bug triage MVP using React/Vite, FastAPI, SQLAlchemy, JWT, and optional OpenAI, Groq, or Google Gemini providers. It includes login, projects, bugs, safe log uploads, AI diagnosis, suggested fixes, test-case generation, and a dashboard.

## Requirements

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ for shared/dev deployment (SQLite works out of the box for a quick local smoke test)
- Optional: OpenAI, Groq, or Google Gemini API key for live AI responses

## 1. Backend Setup (Windows PowerShell)

Open the terminal and run:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit the `.env` file. For the quickest local start, use this configuration if supported by your application:

```env
DATABASE_URL=sqlite:///./bug_detective.db
```

For local development, start the backend:

```powershell
uvicorn app.main:app --reload
```

Open the API documentation:

http://127.0.0.1:8000/docs

Development and test environments create missing tables at startup for convenience. For PostgreSQL or any deployed environment, set `ENVIRONMENT=production`, configure a unique `JWT_SECRET` (at least 32 characters), set `CORS_ORIGINS` to the exact frontend origin(s), and apply migrations before starting the API:

```powershell
cd backend
alembic upgrade head
uvicorn app.main:app
```

Generate a signing secret locally with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Do not use the generated value in source control; place it in the deployment's secret manager or environment configuration. Production startup does not call `create_all()`.

## 2. Frontend Setup (New Terminal)

Open a new terminal from the project root and run:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open the Vite URL shown in the terminal, normally:

http://localhost:5173

## 3. First Login

Register a user using the Register link on the login page.

The first user should be treated as the initial administrator for a demo. This MVP assigns `ADMIN` to the first registered user and `DEVELOPER` to subsequent registrations, if configured in the current backend implementation.

For a real deployment, disable public registration or require an administrator invitation.

## 4. PostgreSQL Setup

Create a database named `bug_detective`:

```sql
CREATE DATABASE bug_detective;
```

Configure the database URL in the backend `.env` file:

```env
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/bug_detective
```

Replace `YOUR_PASSWORD` with your actual PostgreSQL password.

The PostgreSQL driver must be installed, and the database configuration must match the current application setup.

SQLite can be used for quick local testing if supported by the application.

## 5. AI Provider Configuration

- `AI_PROVIDER=mock` works without an API key and returns a clearly labeled heuristic diagnosis.
- For OpenAI, set `AI_PROVIDER=openai`, `AI_API_KEY=YOUR_OPENAI_API_KEY`, and optionally `AI_MODEL=gpt-4o-mini`.
- For Groq, set `AI_PROVIDER=groq`, `AI_API_KEY=YOUR_GROQ_API_KEY`, and optionally `AI_MODEL=llama-3.3-70b-versatile`.
- For Google Gemini, set `AI_PROVIDER=gemini`, `GEMINI_API_KEY=YOUR_GEMINI_API_KEY`, and optionally `GEMINI_MODEL=gemini-3.6-flash`.

Set these values in `backend/.env`; do not commit the file or share the key. A live provider requires a valid key and available provider quota/billing. Missing credentials and provider failures are reported rather than silently switching to mock mode; select `AI_PROVIDER=mock` to use the heuristic analyzer.

Gemini enables analysis generation only. Source-based RAG embeddings remain separately configured through the existing OpenAI-compatible embedding settings; a Gemini API key does not enable Gemini embeddings.

Never commit `.env` files or real API keys. AI outputs are suggestions; review and test them before applying fixes.

## 6. Included MVP Workflow

Login → Create Project → Create Bug → Attach a supported file → Analyze → Review root cause, confidence, suggested fix, and generated test cases.

Potentially supported file formats include:

- LOG
- TXT
- JSON
- PY
- JS
- JSX
- SQL
- PDF
- PNG
- JPG

Text files are decoded as UTF-8. PDFs are checked for validity and unencrypted
documents have selectable text extracted (up to 30 pages). Encrypted PDFs are
accepted with an extraction notice; passwords are never requested or guessed.
Scanned PDF OCR is not configured. PNG/JPG OCR requires both the Python
dependencies and a separately installed Tesseract OCR engine. Set
`TESSERACT_CMD` only when the executable is not on `PATH`. Invalid images and
PDFs are rejected; image processing is capped at 25 million pixels.

Source ZIP uploads can optionally be linked to one of the user's projects in
the upload form. Generated source test cases are stored in PostgreSQL and can
be listed, searched, filtered, paginated, edited, deleted, and exported through
the `/api/test-cases` endpoints. Repeated generation for an upload does not
create duplicate unchanged cases.

Project test runs are recorded in `test_execution_history`, including status,
counts, duration, output, error details, timestamps, and whether isolated
runtime execution actually occurred. When Docker is unavailable, the runner
continues to report static checks as non-runtime results. Execution history is
available from `/api/projects/{upload_id}/execution-history` and has its own
Excel export.

RAG embeddings remain JSON arrays in PostgreSQL; pgvector is not configured.
Stored chunks are reused for retrieval and re-indexed when a later source
analysis supplies changed chunk content. Embedding generation requires the
configured embedding endpoint and credentials described above.

## 7. Checks

Run backend tests from the `backend/` directory:

```powershell
pytest
```

Run the frontend production build from the `frontend/` directory:

```powershell
npm run build
```

Review test results and build output before deploying.

For PostgreSQL schema verification, apply migrations to an isolated database
or schema first:

```powershell
cd backend
alembic upgrade head
```

The automated migration suite uses an isolated SQLite database. It does not
replace a live PostgreSQL integration check.

## 8. Git and GitHub

Check the repository status:

```powershell
git status
```

Stage changes:

```powershell
git add .
```

Commit changes:

```powershell
git commit -m "Update AI Software Bug Detective"
```

Push to the `main` branch:

```powershell
git push origin main
```

If the remote repository contains changes that are not present locally, integrate those changes and resolve any merge conflicts before pushing.

## 9. Production Checklist

- Use a strong, unique `JWT_SECRET`.
- Use PostgreSQL for shared or production environments.
- Enable HTTPS.
- Store uploaded files securely.
- Use managed secrets and environment variables.
- Configure database backups and recovery.
- Apply rate limiting.
- Maintain audit logging.
- Restrict CORS to trusted origins.
- Validate uploaded files and consider malware scanning.
- Control user registration and administrative privileges.
- Review authentication and authorization.
- Keep dependencies updated.
- Test all integrations and security controls before deployment.

This starter is not a claim of production certification. Validate integrations and security for your environment before deployment.

## 10. Security Notes

- Do not upload passwords, API keys, or private credentials to GitHub.
- Keep `.env` files excluded through `.gitignore`.
- Use `.env.example` to document required variables with placeholder values.
- Review AI-generated fixes before using them in your code.
- Confirm that users can access only the projects and bugs they are authorized to view.

## License

Add an appropriate license before distributing this project for reuse.