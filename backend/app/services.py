from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile, HTTPException
from app.config.settings import settings
from app.models import Bug, Project, Attachment

ALLOWED_EXTENSIONS = {".log", ".txt", ".json", ".pdf", ".py", ".js", ".jsx", ".sql", ".png", ".jpg", ".jpeg"}
TEXT_EXTENSIONS = {".log", ".txt", ".json", ".py", ".js", ".jsx", ".sql"}

def ensure_project_access(project: Project, user_id: int):
    # MVP: project owners and ADMIN/MANAGER roles are checked at the route layer.
    return project.owner_id == user_id

def ensure_bug_access(bug: Bug, user_id: int):
    return bug.project.owner_id == user_id

async def save_attachment(upload: UploadFile, bug_id: int, db):
    original = Path(upload.filename or "upload").name
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS: raise HTTPException(400, "Unsupported file type")
    data = await upload.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024: raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit")
    stored = f"{uuid4().hex}{suffix}"
    folder = Path(settings.upload_dir).resolve(); folder.mkdir(parents=True, exist_ok=True)
    target = folder / stored
    target.write_bytes(data)
    extracted = ""
    if suffix in TEXT_EXTENSIONS:
        extracted = data.decode("utf-8", errors="replace")[:20000]
    elif suffix == ".pdf":
        extracted = "PDF uploaded. Text extraction is not enabled in this MVP; copy the relevant error text into the bug description."
    elif suffix in {".png", ".jpg", ".jpeg"}:
        extracted = "Image uploaded. OCR/vision extraction is not enabled in this MVP; transcribe the visible error text into the bug description."
    item = Attachment(bug_id=bug_id, original_name=original[:255], stored_name=stored, content_type=upload.content_type or "application/octet-stream", size_bytes=len(data), extracted_text=extracted)
    db.add(item); db.commit(); db.refresh(item)
    return item
