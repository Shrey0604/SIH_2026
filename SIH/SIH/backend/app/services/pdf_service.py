from __future__ import annotations

import re

import pymupdf


def text_quality(text: str) -> float:
    """A deterministic legibility heuristic, not an AI confidence score."""

    stripped = text.strip()
    if not stripped:
        return 0.0
    printable = sum(character.isprintable() for character in stripped) / len(stripped)
    words = re.findall(r"[A-Za-z0-9]+", stripped)
    length_score = min(len(stripped) / 240.0, 1.0)
    word_score = min(len(words) / 35.0, 1.0)
    return round(printable * 0.35 + length_score * 0.30 + word_score * 0.35, 4)


def validate_pdf(pdf_bytes: bytes) -> int:
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("The uploaded file is not a valid PDF")
    try:
        document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except pymupdf.FileDataError as error:
        raise ValueError("The uploaded PDF could not be opened") from error
    try:
        if document.needs_pass:
            raise ValueError("Password-protected PDFs are not supported")
        if document.page_count < 1:
            raise ValueError("The PDF contains no pages")
        return document.page_count
    finally:
        document.close()


def extract_native_pages(pdf_bytes: bytes, document_id: str) -> list[dict[str, object]]:
    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        pages = []
        for index, page in enumerate(document):
            raw_text = page.get_text("text").strip()
            quality = text_quality(raw_text)
            pages.append(
                {
                    "id": f"page-{document_id}-{index + 1}",
                    "document_id": document_id,
                    "page_number": index + 1,
                    "raw_text": raw_text,
                    "recovered_text": None,
                    "text_quality": quality,
                    "extraction_method": "NATIVE" if quality >= 0.35 else "LOW_TEXT",
                    "width_pt": float(page.rect.width),
                    "height_pt": float(page.rect.height),
                }
            )
        return pages
    finally:
        document.close()


def render_page_for_vision(pdf_bytes: bytes, page_number: int) -> bytes:
    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = document.load_page(page_number - 1)
        return page.get_pixmap(matrix=pymupdf.Matrix(1.7, 1.7), alpha=False).tobytes(
            "png"
        )
    finally:
        document.close()


def chunk_page_text(
    text: str, *, target_chars: int = 1_100, overlap_chars: int = 160
) -> list[str]:
    normalized = re.sub(r"[ \t]+", " ", text).strip()
    if not normalized:
        return []
    if len(normalized) <= 1_500:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + target_chars, len(normalized))
        if end < len(normalized):
            boundary = max(
                normalized.rfind(". ", start + 800, end),
                normalized.rfind("\n", start + 800, end),
            )
            if boundary > start:
                end = boundary + 1
        chunks.append(normalized[start:end].strip())
        if end >= len(normalized):
            break
        start = max(end - overlap_chars, start + 1)
    return [chunk for chunk in chunks if chunk]


def normalized_evidence(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()
