from io import BytesIO
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from app.config.settings import settings
from app.models import Bug, Project, Attachment

ALLOWED_EXTENSIONS = {".log", ".txt", ".json", ".pdf", ".py", ".js", ".jsx", ".sql", ".png", ".jpg", ".jpeg"}
TEXT_EXTENSIONS = {".log", ".txt", ".json", ".py", ".js", ".jsx", ".sql"}
MAX_EXTRACTED_TEXT_CHARS = 20000
MAX_PDF_PAGES = 30
MAX_IMAGE_PIXELS = 25_000_000


def _extract_pdf_text(data: bytes) -> str:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    if not data.startswith(b"%PDF-"):
        raise HTTPException(400, "The uploaded file is not a valid PDF.")
    try:
        reader = PdfReader(BytesIO(data), strict=False)
    except (PdfReadError, OSError, ValueError) as exc:
        raise HTTPException(400, "Unable to read the uploaded PDF.") from exc
    if reader.is_encrypted:
        return "PDF text extraction is unavailable because the document is encrypted."

    try:
        text = "\n".join(
            page.extract_text() or ""
            for page in reader.pages[:MAX_PDF_PAGES]
        )
    except (PdfReadError, OSError, ValueError) as exc:
        raise HTTPException(400, "Unable to extract text from the uploaded PDF.") from exc
    if not text.strip():
        return "No selectable text was found in the PDF. Scanned pages require OCR."
    return text[:MAX_EXTRACTED_TEXT_CHARS]


def _extract_image_text(data: bytes, suffix: str) -> str:
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(BytesIO(data)) as image:
            expected_format = "PNG" if suffix == ".png" else "JPEG"
            if image.format != expected_format:
                raise HTTPException(400, "The image content does not match its file extension.")
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise HTTPException(413, "Image dimensions exceed the OCR processing limit.")
            image.load()
            ocr_image = image.convert("RGB")
    except HTTPException:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(400, "Unable to read the uploaded image.") from exc

    try:
        import pytesseract
    except ImportError:
        return "Image uploaded, but OCR is unavailable. Install pytesseract and the Tesseract OCR engine."
    if settings.tesseract_cmd.strip():
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd.strip()
    try:
        text = pytesseract.image_to_string(ocr_image, timeout=20)
    except pytesseract.pytesseract.TesseractNotFoundError:
        return "Image uploaded, but OCR is unavailable. Install Tesseract OCR or configure TESSERACT_CMD."
    except pytesseract.pytesseract.TesseractError as exc:
        raise HTTPException(422, "OCR could not process the uploaded image.") from exc
    except RuntimeError as exc:
        message = (
            "OCR processing timed out."
            if str(exc) == "Tesseract process timeout"
            else "OCR could not process the uploaded image."
        )
        raise HTTPException(422, message) from exc
    if not text.strip():
        return "OCR could not read text from the image. Attach a clearer image or enter the error text manually."
    return text[:MAX_EXTRACTED_TEXT_CHARS]

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
    extracted = ""
    if suffix in TEXT_EXTENSIONS:
        extracted = data.decode("utf-8", errors="replace")[:MAX_EXTRACTED_TEXT_CHARS]
    elif suffix == ".pdf":
        extracted = _extract_pdf_text(data)
    elif suffix in {".png", ".jpg", ".jpeg"}:
        extracted = _extract_image_text(data, suffix)

    stored = f"{uuid4().hex}{suffix}"
    folder = Path(settings.upload_dir).resolve(); folder.mkdir(parents=True, exist_ok=True)
    target = folder / stored
    try:
        target.write_bytes(data)
    except OSError:
        target.unlink(missing_ok=True)
        raise
    item = Attachment(bug_id=bug_id, original_name=original[:255], stored_name=stored, content_type=upload.content_type or "application/octet-stream", size_bytes=len(data), extracted_text=extracted)
    try:
        db.add(item)
        db.commit()
        db.refresh(item)
    except SQLAlchemyError:
        db.rollback()
        target.unlink(missing_ok=True)
        raise
    return item
