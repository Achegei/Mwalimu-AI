import re
from dataclasses import dataclass
from io import BytesIO

from docx import Document as DocxDocument
from pypdf import PdfReader


DOCX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int | None
    text: str


@dataclass(frozen=True)
class DocumentChunkData:
    chunk_index: int
    content: str
    page_number: int | None
    character_count: int


def normalize_text(text: str) -> str:
    """
    Normalize extracted text into stable whitespace.

    Extraction libraries frequently return repeated spaces,
    tabs, newlines, and page-layout whitespace. For the first
    ingestion version we normalize these into single spaces.
    """

    return re.sub(r"\s+", " ", text).strip()


def _extract_plain_text(
    content: bytes,
) -> list[ExtractedPage]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "Plain-text document must be UTF-8 encoded."
        ) from exc

    text = normalize_text(text)

    if not text:
        raise ValueError(
            "Document contains no extractable text."
        )

    return [
        ExtractedPage(
            page_number=None,
            text=text,
        )
    ]


def _extract_docx(
    content: bytes,
) -> list[ExtractedPage]:
    try:
        document = DocxDocument(
            BytesIO(content)
        )
    except Exception as exc:
        raise ValueError(
            "Unable to read DOCX document."
        ) from exc

    parts = []

    for paragraph in document.paragraphs:
        text = normalize_text(
            paragraph.text
        )

        if text:
            parts.append(text)

    text = normalize_text(
        " ".join(parts)
    )

    if not text:
        raise ValueError(
            "Document contains no extractable text."
        )

    # DOCX does not expose reliable rendered page
    # boundaries because pagination depends on the
    # rendering environment.
    return [
        ExtractedPage(
            page_number=None,
            text=text,
        )
    ]


def _extract_pdf(
    content: bytes,
) -> list[ExtractedPage]:
    try:
        reader = PdfReader(
            BytesIO(content)
        )
    except Exception as exc:
        raise ValueError(
            "Unable to read PDF document."
        ) from exc

    pages: list[ExtractedPage] = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        try:
            raw_text = page.extract_text() or ""
        except Exception as exc:
            raise ValueError(
                f"Unable to extract text from PDF page "
                f"{page_number}."
            ) from exc

        text = normalize_text(
            raw_text
        )

        if not text:
            continue

        pages.append(
            ExtractedPage(
                page_number=page_number,
                text=text,
            )
        )

    if not pages:
        raise ValueError(
            "PDF contains no extractable text. "
            "It may be a scanned or image-only document."
        )

    return pages


def extract_document_text(
    content: bytes,
    *,
    mime_type: str,
    filename: str,
) -> list[ExtractedPage]:
    """
    Extract normalized text from a supported document.

    Supported in the first ingestion version:
    - PDF
    - DOCX
    - UTF-8 plain text
    """

    normalized_mime = (
        mime_type
        .split(";", 1)[0]
        .strip()
        .lower()
    )

    normalized_filename = (
        filename
        .strip()
        .lower()
    )

    if (
        normalized_mime == "application/pdf"
        or normalized_filename.endswith(".pdf")
    ):
        return _extract_pdf(content)

    if (
        normalized_mime == DOCX_MIME_TYPE
        or normalized_filename.endswith(".docx")
    ):
        return _extract_docx(content)

    if (
        normalized_mime == "text/plain"
        or normalized_filename.endswith(".txt")
    ):
        return _extract_plain_text(
            content
        )

    raise ValueError(
        "Unsupported document format. "
        "Supported formats are PDF, DOCX, and TXT."
    )


def _split_text(
    text: str,
    *,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    """
    Split normalized text into character-bounded chunks.

    Whenever possible, chunk boundaries are moved backward
    to whitespace so words are not split in the middle.
    """

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(
            start + chunk_size,
            text_length,
        )

        if end < text_length:
            boundary = text.rfind(
                " ",
                start,
                end,
            )

            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        next_start = max(
            0,
            end - overlap,
        )

        # Move forward past whitespace left by the
        # previous boundary without discarding overlap
        # content unnecessarily.
        while (
            next_start < text_length
            and text[next_start].isspace()
        ):
            next_start += 1

        # Defensive progress guard.
        if next_start <= start:
            next_start = end

        start = next_start

    return chunks


def chunk_extracted_pages(
    pages: list[ExtractedPage],
    *,
    chunk_size: int = 1500,
    overlap: int = 200,
) -> list[DocumentChunkData]:
    """
    Chunk extracted pages while preserving page provenance.

    Chunks never cross page boundaries. This gives future
    retrieval responses a stable source page when the source
    format exposes page numbers.
    """

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than zero."
        )

    if overlap < 0:
        raise ValueError(
            "overlap cannot be negative."
        )

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size."
        )

    chunks: list[DocumentChunkData] = []
    chunk_index = 0

    for page in pages:
        text = normalize_text(
            page.text
        )

        if not text:
            continue

        for content in _split_text(
            text,
            chunk_size=chunk_size,
            overlap=overlap,
        ):
            chunks.append(
                DocumentChunkData(
                    chunk_index=chunk_index,
                    content=content,
                    page_number=page.page_number,
                    character_count=len(content),
                )
            )

            chunk_index += 1

    if not chunks:
        raise ValueError(
            "Document contains no text available for chunking."
        )

    return chunks
