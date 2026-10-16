# AI Software Bug Detective

AI-assisted bug triage MVP using React/Vite, FastAPI, SQLAlchemy, JWT, and an optional OpenAI/Groq provider. It includes login, projects, bugs, safe log uploads, AI diagnosis, suggested fixes, test-case generation, and a dashboard.

## Requirements

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ for shared/dev deployment (SQLite works out of the box for a quick local smoke test)
- Optional: OpenAI or Groq API key for live AI responses

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

Start the backend:

```powershell
uvicorn app.main:app --reload
```

Open the API documentation:

http://127.0.0.1:8000/docs

The app creates database tables on startup for this MVP, depending on the current configuration.

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

Use model names supported by your provider and current integration.

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

Actual upload support depends on the backend validation and current implementation.

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