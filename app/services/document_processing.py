from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.enums import DocumentProcessingStatus
from app.services.document_ingestion import (
    chunk_extracted_pages,
    extract_document_text,
)
from app.services.document_storage import (
    read_document_bytes,
)


async def process_document(
    db: AsyncSession,
    document_id: int,
    *,
    chunk_size: int = 1500,
    overlap: int = 200,
) -> dict:
    """
    Extract, chunk, and persist one uploaded document.

    Successful reprocessing replaces the document's previous
    chunks. Failed processing records the failure on the
    document while preserving database consistency.
    """

    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
        )
    )

    document = result.scalar_one_or_none()

    if document is None:
        raise ValueError(
            "Document not found."
        )

    document.processing_status = (
        DocumentProcessingStatus.PROCESSING
    )
    document.error_message = None

    await db.commit()

    try:
        content = read_document_bytes(
            document.storage_key,
        )

        pages = extract_document_text(
            content,
            mime_type=document.mime_type,
            filename=document.original_filename,
        )

        chunks = chunk_extracted_pages(
            pages,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        await db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document.id,
            )
        )

        for chunk in chunks:
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    page_number=chunk.page_number,
                    character_count=chunk.character_count,
                    metadata_json=None,
                )
            )

        document.processing_status = (
            DocumentProcessingStatus.READY
        )
        document.error_message = None

        await db.commit()

        return {
            "document_id": document.id,
            "chunk_count": len(chunks),
            "processing_status": (
                DocumentProcessingStatus.READY
            ),
        }

    except Exception as exc:
        await db.rollback()

        failed_result = await db.execute(
            select(Document).where(
                Document.id == document_id,
            )
        )

        failed_document = (
            failed_result.scalar_one_or_none()
        )

        if failed_document is not None:
            failed_document.processing_status = (
                DocumentProcessingStatus.FAILED
            )
            failed_document.error_message = str(exc)

            await db.commit()

        raise
