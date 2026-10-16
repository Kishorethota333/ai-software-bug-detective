# Pin-to-pin setup and feature checklist

## A. Start services
1. Install Python 3.10+ and Node.js 18+.
2. Open terminal A; go to `backend`; create and activate `.venv`.
3. Run `pip install -r requirements.txt`; copy `.env.example` to `.env`.
4. Start with `uvicorn app.main:app --reload`. Check `/api/health` and `/docs`.
5. Open terminal B; go to `frontend`; run `npm install`, copy `.env.example` to `.env`, then `npm run dev`.
6. Register from the UI. The first account becomes ADMIN in this demo; later accounts become DEVELOPER.
7. Create a project, create a bug, upload an allowed file, then run AI analysis.

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
- React/Vite responsive UI; JWT login/register; dashboard; project CRUD; bug CRUD; attachment upload with extension and size checks; heuristic or OpenAI/Groq analysis; persisted diagnosis and test cases; test-case execution flag; API health endpoint; smoke test.

## D. Deliberately not represented as complete
- pgvector embeddings/RAG retrieval, screenshot OCR/vision, PDF text extraction, repository/GitHub integration, notifications/email/Slack, risk prediction, team membership/invitations, complete audit log, migrations, and production deployment hardening. These are advanced phases in the source requirements, not silently simulated as implemented. Image/PDF files can be uploaded, but the current MVP asks users to paste visible error text manually.

## E. Verification
- Backend: `cd backend; pytest`
- Frontend: `cd frontend; npm run build`
- Manual: register/login, create project, create bug, upload a small `.log`, run analysis, reload the bug, and check persisted analysis/test cases.

## F. Security before production
Rotate JWT secret; use PostgreSQL; disable or gate public registration; restrict CORS; serve HTTPS; use private object storage and malware scanning; add Alembic migrations, rate limiting, audit events, backups, monitoring, authorization review, and provider timeouts/retry policies. Avoid logging credentials and do not upload sensitive data.
