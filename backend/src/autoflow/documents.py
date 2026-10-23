"""
Read text out of documents: plain text, PDFs, scans and photos.

- Text files are decoded directly.
- PDFs with a text layer are read with pypdf.
- Scanned PDFs and images are transcribed by an AI model (OCR), when
  allow_ai is set and a provider is configured.

The file type is detected from the content itself, never trusted from
the file name or the sender's content type.
"""

import io

from autoflow.ai import providers


MAX_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 100_000
# Below this many characters per page, a PDF is treated as a scan
SCAN_THRESHOLD_PER_PAGE = 20

IMAGE_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF8": "image/gif",
}


class DocumentError(ValueError):
    """The document cannot be read."""


def detect_type(data):
    if data.startswith(b"%PDF"):
        return "application/pdf"
    for signature, mime in IMAGE_SIGNATURES.items():
        if data.startswith(signature):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    try:
        data[:4096].decode("utf-8")
        return "text/plain"
    except UnicodeDecodeError:
        return "application/octet-stream"


def _limit(text):
    text = text.strip()
    return text[:MAX_TEXT_CHARS], len(text) > MAX_TEXT_CHARS


def _ocr(data, mime_type):
    try:
        text, provider = providers.transcribe(data, mime_type)
    except providers.AIUnavailable as error:
        raise DocumentError(f"This looks like a scan or photo, but it could not be read: {error}") from error
    return text, provider


def extract_text(data, filename="", allow_ai=True):
    """Return {"filename", "content_type", "size", "text", "pages", "method", "truncated"}."""

    if not data:
        raise DocumentError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise DocumentError(f"The file is larger than {MAX_BYTES // (1024 * 1024)} MB.")

    content_type = detect_type(data)
    pages = None

    if content_type == "text/plain":
        text, method = data.decode("utf-8", errors="replace"), "text"

    elif content_type == "application/pdf":
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            reader = PdfReader(io.BytesIO(data))
            pages = len(reader.pages)
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        except (PdfReadError, ValueError, KeyError) as error:
            raise DocumentError(f"The PDF could not be read: {error}") from error

        method = "pdf"
        if len(text.strip()) < SCAN_THRESHOLD_PER_PAGE * max(pages, 1):
            if not allow_ai:
                raise DocumentError("This PDF is a scan; reading it needs AI, which is not allowed here.")
            text, provider = _ocr(data, content_type)
            method = f"ai_ocr:{provider}"

    elif content_type.startswith("image/"):
        if not allow_ai:
            raise DocumentError("Reading images needs AI, which is not allowed here.")
        text, provider = _ocr(data, content_type)
        method = f"ai_ocr:{provider}"

    else:
        raise DocumentError("Unsupported file type. Use PDF, PNG, JPEG, GIF, WebP or text.")

    text, truncated = _limit(text)
    return {
        "filename": filename,
        "content_type": content_type,
        "size": len(data),
        "text": text,
        "pages": pages,
        "method": method,
        "truncated": truncated,
    }
