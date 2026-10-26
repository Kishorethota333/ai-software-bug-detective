from math import sqrt

import httpx
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models import SourceChunk


MAX_CHUNK_CHARS = 1800
CHUNK_OVERLAP_CHARS = 200
MAX_INDEX_CHUNKS = 256


class EmbeddingUnavailable(Exception):
    pass


def chunk_documents(documents: list[tuple[str, str]]) -> list[dict]:
    chunks = []
    for source_name, text in documents:
        text = text.strip()
        start = 0
        chunk_index = 0
        while start < len(text) and len(chunks) < MAX_INDEX_CHUNKS:
            end = min(start + MAX_CHUNK_CHARS, len(text))
            if end < len(text):
                boundary = text.rfind("\n", start + MAX_CHUNK_CHARS // 2, end)
                if boundary > start:
                    end = boundary
            content = text[start:end].strip()
            if content:
                chunks.append({
                    "source_name": source_name,
                    "chunk_index": chunk_index,
                    "content": f"Source file: {source_name}\n{content}",
                })
                chunk_index += 1
            if end >= len(text):
                break
            start = max(start + 1, end - CHUNK_OVERLAP_CHARS)
    return chunks


def _embedding_credentials() -> tuple[str, str]:
    api_url = settings.rag_embedding_api_url.strip()
    api_key = settings.rag_embedding_api_key.strip()
    if not api_url and settings.ai_provider.lower().strip() == "openai":
        api_url = "https://api.openai.com/v1/embeddings"
        api_key = api_key or settings.ai_api_key.strip()
    if not api_url or not api_key:
        raise EmbeddingUnavailable(
            "Embedding service is not configured. Set AI_PROVIDER=openai and AI_API_KEY, "
            "or set RAG_EMBEDDING_API_URL and RAG_EMBEDDING_API_KEY."
        )
    return api_url, api_key


async def embed_texts(texts: list[str]) -> list[list[float]]:
    api_url, api_key = _embedding_credentials()
    vectors = []
    async with httpx.AsyncClient(timeout=45) as client:
        for offset in range(0, len(texts), 64):
            batch = texts[offset:offset + 64]
            response = await client.post(
                api_url,
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": settings.rag_embedding_model, "input": batch},
            )
            response.raise_for_status()
            data = response.json().get("data", [])
            if len(data) != len(batch):
                raise ValueError("Embedding service returned an unexpected vector count.")
            ordered = sorted(data, key=lambda item: item.get("index", 0))
            for item in ordered:
                vector = item.get("embedding")
                if not isinstance(vector, list) or not vector or any(
                    not isinstance(value, (int, float)) for value in vector
                ):
                    raise ValueError("Embedding service returned an invalid vector.")
                vectors.append([float(value) for value in vector])
    return vectors


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return -1.0
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return -1.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


async def retrieve_source_context(
    db: Session,
    upload_id: str,
    owner_id: int,
    query: str,
    documents: list[tuple[str, str]],
    limit: int = 5,
) -> dict:
    try:
        existing = db.query(SourceChunk).filter_by(
            upload_id=upload_id,
            owner_id=owner_id,
        ).count()
        chunks = []
        if not existing:
            chunks = chunk_documents(documents)
            if not chunks:
                return {"status": "UNAVAILABLE", "message": "No supported source text was available to index.", "chunks": []}

        vectors = await embed_texts([chunk["content"] for chunk in chunks]) if chunks else []
        query_vector = (await embed_texts([query]))[0]

        if chunks:
            if any(len(vector) != len(vectors[0]) for vector in vectors):
                raise ValueError("Embedding service returned vectors with inconsistent dimensions.")
            db.query(SourceChunk).filter_by(upload_id=upload_id, owner_id=owner_id).delete()
            db.add_all([
                SourceChunk(
                    upload_id=upload_id,
                    owner_id=owner_id,
                    source_name=chunk["source_name"],
                    chunk_index=chunk["chunk_index"],
                    content=chunk["content"],
                    embedding=vector,
                )
                for chunk, vector in zip(chunks, vectors)
            ])
            db.commit()

        stored_chunks = db.query(SourceChunk).filter_by(
            upload_id=upload_id,
            owner_id=owner_id,
        ).all()
        if stored_chunks and any(
            len(chunk.embedding) != len(query_vector)
            for chunk in stored_chunks
        ):
            return {
                "status": "UNAVAILABLE",
                "message": "Embedding dimensions do not match the stored source vectors; reindex with the configured embedding model.",
                "chunks": [],
            }
        ranked = sorted(
            ((_cosine_similarity(chunk.embedding, query_vector), chunk) for chunk in stored_chunks),
            key=lambda item: item[0],
            reverse=True,
        )
        selected = [
            {"source_name": chunk.source_name, "content": chunk.content, "score": round(score, 4)}
            for score, chunk in ranked[:limit]
            if score >= 0
        ]
        return {"status": "RETRIEVED", "message": "Retrieved source chunks by embedding similarity.", "chunks": selected}
    except EmbeddingUnavailable as exc:
        return {"status": "UNAVAILABLE", "message": str(exc), "chunks": []}
    except httpx.HTTPStatusError as exc:
        return {
            "status": "UNAVAILABLE",
            "message": f"Embedding service returned HTTP {exc.response.status_code}; verify the endpoint, model, and credentials.",
            "chunks": [],
        }
    except (httpx.RequestError, ValueError, KeyError, TypeError) as exc:
        return {
            "status": "UNAVAILABLE",
            "message": f"Embedding service could not provide usable vectors ({type(exc).__name__}).",
            "chunks": [],
        }