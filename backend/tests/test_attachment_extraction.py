from io import BytesIO

import pytest
from fastapi import HTTPException
from PIL import Image
from pypdf import PdfWriter

from app import services


def _pdf_bytes(encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    if encrypted:
        writer.encrypt("sample-password")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (4, 4), color="white").save(output, format="PNG")
    return output.getvalue()


def test_pdf_extraction_handles_empty_encrypted_and_invalid_documents():
    assert "No selectable text" in services._extract_pdf_text(_pdf_bytes())
    assert "encrypted" in services._extract_pdf_text(_pdf_bytes(encrypted=True))

    with pytest.raises(HTTPException) as error:
        services._extract_pdf_text(b"not a pdf")
    assert error.value.status_code == 400


def test_image_extraction_runs_ocr_and_reports_unreadable_images(monkeypatch):
    import pytesseract

    monkeypatch.setattr(
        pytesseract,
        "image_to_string",
        lambda _image, timeout: "ValueError: unexpected input",
    )
    assert services._extract_image_text(_png_bytes(), ".png") == (
        "ValueError: unexpected input"
    )

    with pytest.raises(HTTPException) as error:
        services._extract_image_text(b"not an image", ".png")
    assert error.value.status_code == 400

    with pytest.raises(HTTPException) as mismatch:
        services._extract_image_text(_png_bytes(), ".jpg")
    assert mismatch.value.status_code == 400


def test_image_extraction_reports_ocr_timeout(monkeypatch):
    import pytesseract

    def raise_timeout(_image, timeout):
        assert timeout == 20
        raise RuntimeError("Tesseract process timeout")

    monkeypatch.setattr(pytesseract, "image_to_string", raise_timeout)

    with pytest.raises(HTTPException) as error:
        services._extract_image_text(_png_bytes(), ".png")

    assert error.value.status_code == 422
    assert error.value.detail == "OCR processing timed out."


def test_image_extraction_respects_pixel_limit(monkeypatch):
    monkeypatch.setattr(services, "MAX_IMAGE_PIXELS", 4)

    with pytest.raises(HTTPException) as error:
        services._extract_image_text(_png_bytes(), ".png")
    assert error.value.status_code == 413
