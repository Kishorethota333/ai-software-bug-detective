import asyncio
import io
import uuid
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.ai import rag
from app.config.database import Base, get_db
from app.models import ProjectUpload, SourceChunk, User


@pytest.fixture
def rag_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = session_factory()
    user = User(name="RAG Test", email=f"rag-{uuid.uuid4().hex}@example.com", password_hash="test")
    db.add(user)
    db.flush()
    db.add(ProjectUpload(upload_id="a" * 32, owner_id=user.id))
    db.commit()
    try:
        yield db, user
    finally:
        db.close()
        engine.dispose()


def test_chunk_documents_splits_source_with_overlap():
    chunks = rag.chunk_documents([("src/example.py", "x" * 4000)])

    assert len(chunks) > 1
    assert all(chunk["source_name"] == "src/example.py" for chunk in chunks)
    assert all("Source file: src/example.py" in chunk["content"] for chunk in chunks)
    first_text = chunks[0]["content"].split("\n", 1)[1]
    second_text = chunks[1]["content"].split("\n", 1)[1]
    assert first_text[-rag.CHUNK_OVERLAP_CHARS:] == second_text[:rag.CHUNK_OVERLAP_CHARS]


def test_retrieval_persists_embeddings_and_ranks_by_similarity(rag_session, monkeypatch):
    db, user = rag_session
    calls = []

    async def fake_embed_texts(texts):
        calls.append(texts)
        return [[1.0, 0.0] if "matching" in text.lower() else [0.0, 1.0] for text in texts]

    monkeypatch.setattr(rag, "embed_texts", fake_embed_texts)
    documents = [
        ("src/matching.py", "matching behavior"),
        ("src/other.py", "unrelated behavior"),
    ]

    result = asyncio.run(rag.retrieve_source_context(
        db, "a" * 32, user.id, "matching query", documents
    ))

    assert result["status"] == "RETRIEVED"
    assert result["chunks"][0]["source_name"] == "src/matching.py"
    assert db.query(SourceChunk).filter_by(upload_id="a" * 32, owner_id=user.id).count() == 2

    reused = asyncio.run(rag.retrieve_source_context(
        db, "a" * 32, user.id, "matching query", []
    ))
    assert reused["chunks"][0]["source_name"] == "src/matching.py"
    assert len(calls) == 3


def test_retrieval_reports_missing_embedding_configuration(rag_session, monkeypatch):
    db, user = rag_session
    monkeypatch.setattr(rag.settings, "ai_provider", "mock")
    monkeypatch.setattr(rag.settings, "ai_api_key", "")
    monkeypatch.setattr(rag.settings, "rag_embedding_api_url", "")
    monkeypatch.setattr(rag.settings, "rag_embedding_api_key", "")

    result = asyncio.run(rag.retrieve_source_context(
        db, "a" * 32, user.id, "query", [("src/example.py", "source")]
    ))

    assert result["status"] == "UNAVAILABLE"
    assert "Set AI_PROVIDER=openai and AI_API_KEY" in result["message"]
    assert not result["chunks"]
    assert db.query(SourceChunk).count() == 0


def test_retrieval_reports_embedding_dimension_mismatch(rag_session, monkeypatch):
    db, user = rag_session
    db.add(SourceChunk(
        upload_id="a" * 32,
        owner_id=user.id,
        source_name="src/example.py",
        chunk_index=0,
        content="indexed source",
        embedding=[1.0, 0.0],
    ))
    db.commit()

    async def mismatched_embed_texts(texts):
        return [[1.0] for _ in texts]

    monkeypatch.setattr(rag, "embed_texts", mismatched_embed_texts)
    result = asyncio.run(rag.retrieve_source_context(
        db, "a" * 32, user.id, "query", []
    ))

    assert result["status"] == "UNAVAILABLE"
    assert "dimensions do not match" in result["message"]
    assert not result["chunks"]


def test_generation_injects_retrieved_chunks_into_ai_prompt(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(main, "PROJECT_UPLOAD_DIR", tmp_path)
    main.app.dependency_overrides[get_db] = override_get_db
    captured = {}

    async def fake_embed_texts(texts):
        return [
            [1.0, 0.0]
            if "source file:" not in text.lower() or "matching" in text.lower()
            else [0.0, 1.0]
            for text in texts
        ]

    async def fake_analyze(context):
        captured["context"] = context
        return {
            "test_cases": [{
                "scenario": "Check retrieved behavior",
                "input_data": "valid input",
                "expected_result": "success",
                "priority": "HIGH",
                "test_type": "REGRESSION",
            }],
            "provider": "mock",
        }

    monkeypatch.setattr(rag, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(main, "analyze", fake_analyze)
    try:
        with TestClient(main.app) as client:
            registration = client.post(
                "/api/auth/register",
                json={
                    "name": "RAG Route Test",
                    "email": f"rag-route-{uuid.uuid4().hex}@example.com",
                    "password": "test-password-123",
                },
            )
            headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
            payload = io.BytesIO()
            with zipfile.ZipFile(payload, "w") as archive:
                archive.writestr("project/src/matching.py", "matching behavior sentinel")
                for index in range(5):
                    archive.writestr(
                        f"project/src/unrelated-{index}.py",
                        f"unrelated behavior sentinel {index}",
                    )
            uploaded = client.post(
                "/api/projects/upload-source",
                headers=headers,
                files={"file": ("project.zip", payload.getvalue(), "application/zip")},
            )
            assert uploaded.status_code == 200, uploaded.text

            response = client.post(
                f"/api/projects/{uploaded.json()['upload_id']}/generate-test-cases",
                headers=headers,
            )

        assert response.status_code == 200, response.text
        assert response.json()["rag"]["status"] == "RETRIEVED"
        assert response.json()["rag"]["retrieved_chunks"] == 5
        assert "RETRIEVED SOURCE CONTEXT" in captured["context"]
        assert "Source file: project/src/matching.py" in captured["context"]
        assert "unrelated behavior sentinel 4" not in captured["context"]
    finally:
        main.app.dependency_overrides.pop(get_db, None)
        engine.dispose()