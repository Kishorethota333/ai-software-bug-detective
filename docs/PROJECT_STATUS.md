# Project Delivery Status

## Summary

Current delivery status is **75% (6 of 8 original checklist items)**. This counts implemented and tested behavior; it does not imply live external integrations are verified. No code was changed for this status report, and no database migration was run.

## Original Requirements Checklist

| Requirement | Status | Evidence |
| --- | --- | --- |
| RAG pipeline: source chunking, embeddings, vector storage, similarity retrieval, and prompt injection | PASS, controlled test evidence | `backend/tests/test_rag.py` covers chunking, persisted vectors, similarity ranking, prompt injection, and unavailable-service responses. These tests use controlled embeddings. Live embedding retrieval is not verified. |
| Real AI provider | NOT VERIFIED | Provider integration exists. Current configuration is `AI_PROVIDER=mock`; no AI API key is configured, and no live provider call was verified. |
| Backend tests and core API workflows | PASS | Latest recorded backend suite: 27 passed. Existing smoke coverage exercises registration, project/bug creation, mock analysis, test cases, and test-case Excel export. |
| Frontend production build | PASS | Latest recorded `npm run build` succeeded. |
| Authorization | PASS | JWT authentication and project ownership checks are implemented; backend tests passed, including unauthenticated upload rejection. |
| Isolated runtime execution | NOT VERIFIED | Docker command is unavailable on PATH. The implementation uses a Docker runner and explicitly falls back to static checks when Docker is unavailable. No uploaded code was executed on the host. |
| Uploaded-code execution safety | PASS | Static analysis/fallback does not execute uploaded source on the host; upload validation tests passed. |
| Project-upload Excel report download | PASS, user-reported browser evidence | The user reports that the project-upload Excel report downloaded successfully in the browser. This was not independently repeated for this document. |

## RAG And AI Setup

RAG source retrieval is implemented for source-based test-case generation. Chunks and embeddings are stored in the SQLAlchemy database and selected by cosine similarity before being injected into the generation prompt.

The current environment has no configured live provider credentials. For OpenAI embeddings, configure `AI_PROVIDER=openai` and `AI_API_KEY`. For a compatible alternative, configure `RAG_EMBEDDING_API_URL` and `RAG_EMBEDDING_API_KEY`; `RAG_EMBEDDING_MODEL` is optional and defaults to `text-embedding-3-small`. Live AI generation also requires a supported provider and `AI_API_KEY`. Do not put credential values in this document or source control.

Controlled embedding tests are not evidence that live embeddings, live RAG retrieval, or a live AI provider call work. Source code may be sent to the configured embedding and AI services; upload only content approved for those services and remove secrets first.

## Runtime And Database

Docker is unavailable in the checked environment, so actual isolated runtime execution is not verified. Do not run uploaded projects directly on the host. To verify runtime later, install and start Docker, provide the configured `ai-bug-detective-python-runner:latest` image, and use a trusted sample upload through the isolated runner.

The additive Alembic migration `9d7e2f1c4a60_add_source_chunks_for_rag.py` creates the RAG chunk table. It has not been applied to the configured database. For an Alembic-managed deployment, review and run `python -m alembic upgrade head` against the intended database before using persisted RAG. The app also creates missing SQLAlchemy tables at startup in the current MVP configuration.

## Startup And Verification Commands

From the repository root, start the backend in one PowerShell terminal:

```powershell
Set-Location .\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Start the frontend in a second PowerShell terminal:

```powershell
Set-Location .\frontend
npm run dev
```

Previously recorded verification commands and results:

```powershell
Set-Location .\backend
python -m pytest -q
# 27 passed
```

```powershell
Set-Location .\frontend
npm run build
# Vite production build succeeded
```

The Excel report browser download is user-reported evidence. No tests or migrations were run while preparing this document.

## Known Limitations And Remaining Work

- Configure credentials and perform a real embedding plus AI-provider workflow to verify live RAG end to end.
- Enable Docker and verify one isolated runtime run; current runtime behavior is the safe static fallback.
- Apply the additive migration only after confirming the intended database and migration process.
- Existing stored chunks are not associated with an embedding-model identifier. Keep the embedding model stable; changing models may require manually rebuilding existing vectors.
- RAG currently applies to source-based test-case generation, not bug-report diagnosis.
- Continue production hardening described in `PIN_TO_PIN_SETUP.md`, including secret management, registration policy, HTTPS, CORS restrictions, backups, and deployment review.
