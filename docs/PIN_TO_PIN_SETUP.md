# Pin-to-pin setup and feature checklist

## A. Start services
1. Install Python 3.10+ and Node.js 18+.
2. Open terminal A; go to `backend`; create and activate `.venv`.
3. Run `pip install -r requirements.txt`. Copy `.env.example` to `.env` only if a local `.env` does not already exist; do not overwrite existing credentials.
4. Configure the backend environment variable names required for your setup: `DATABASE_URL`, `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `CORS_ORIGINS`, `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `RAG_EMBEDDING_API_URL`, `RAG_EMBEDDING_API_KEY`, and `RAG_EMBEDDING_MODEL`. Keep all secret values only in the ignored backend `.env`.
5. Start with `uvicorn app.main:app --reload`. Check `/api/health` and `/docs`.
6. Open terminal B; go to `frontend`; run `npm install`, copy the frontend `.env.example` only if its `.env` does not already exist, then run `npm run dev`.
7. Register from the UI. The first account becomes ADMIN in this demo; later accounts become DEVELOPER.
8. Create a project, create a bug, upload an allowed file, then run AI analysis.

## B. API sequence
- `POST /api/auth/register` or `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/projects`, `GET /api/projects`
- `POST /api/bugs`, `GET /api/bugs`, `GET /api/bugs/{id}`
- `POST /api/bugs/{id}/attachments` (multipart form field `file`)
- `POST /api/bugs/{id}/analyze`
- `GET /api/bugs/{id}/analyses`, `GET /api/test-cases`
- `GET /api/dashboard`

## C. Implemented in this starter
- React/Vite responsive UI; JWT login/register; dashboard; project CRUD; bug CRUD; attachment upload with extension and size checks; heuristic or OpenAI/Groq/Gemini analysis; persisted diagnosis and test cases; test-case execution flag; API health endpoint; smoke test.
- Gemini uses `AI_PROVIDER=gemini`, `GEMINI_API_KEY`, and optional `GEMINI_MODEL` (default `gemini-3.6-flash`). OpenAI/Groq use `AI_API_KEY` and `AI_MODEL`; explicit `AI_PROVIDER=mock` remains available.
- RAG source retrieval for source-based test-case generation uses an OpenAI-compatible embedding endpoint and SQLAlchemy JSON-stored vectors. Gemini generation credentials do not configure embeddings.

## D. Deliberately not represented as complete
- Live RAG embedding/retrieval is not verified; the RAG tests use fake embeddings. The project stores vectors as JSON in SQLAlchemy, not pgvector. Screenshot OCR/vision, PDF text extraction, repository/GitHub integration, notifications/email/Slack, risk prediction, team membership/invitations, complete audit log, migrations, and production deployment hardening are also incomplete. These are not silently simulated as implemented. Image/PDF files can be uploaded, but the current MVP asks users to paste visible error text manually.
- Generated test cases are recommendations. Do not treat them as executed tests or run uploaded code on the host. The project test runner uses Docker isolation when available and otherwise performs static checks only; static checks do not execute the uploaded project or generated tests. No Docker or uploaded-code execution is part of the current verification.

## E. Verification
- Latest targeted backend tests (`test_ai_analyzer.py`, `test_rag.py`, `test_project_upload_validation.py`, and `test_smoke.py`): 38 passed using isolated SQLite and temporary upload storage. This was not a full-suite run.
- Frontend: `npm run build` succeeded.
- Live Gemini analysis: an authenticated isolated ZeroDivisionError analysis API request returned HTTP 200. A final live analyzer request returned generated cases for `10 / 2 = 5` and controlled handling of `10 / 0`. Generated cases were not executed.
- RAG retrieval/context injection passed controlled tests with fake embeddings. Live embedding/retrieval remains blocked until an embedding endpoint and key are configured, or the OpenAI fallback credentials are configured.
- The project has no configured Playwright tests. Browser display of a live Gemini diagnosis and the complete UI workflow remain unverified.
- No production database records, migrations, Docker, or uploaded project code were used for these tests.
- Manual follow-up: sign in, create a temporary/demo project and bug, run analysis, inspect diagnosis/test cases, and verify persisted results. Use an isolated test database for any non-demo test data.

## F. Security before production
Rotate/set a strong JWT secret; use PostgreSQL with an approved migration plan; disable or gate public registration; restrict CORS; serve HTTPS; use private object storage and malware scanning; add rate limiting, audit events, backups, monitoring, expired-token and attachment-ownership tests, and provider timeout/retry review. Avoid logging credentials and do not upload sensitive data. The current backend tests cover unauthenticated requests, selected ownership checks, ZIP path traversal, size limits, and secret-file filtering; they do not constitute a complete production security review.
