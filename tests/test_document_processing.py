from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.content import Subject
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.enums import (
    DocumentProcessingStatus,
    DocumentType,
)
from app.services.document_processing import process_document
from app.services.document_storage import save_document_bytes


async def create_document(
    db_session,
    *,
    school_id: int,
    uploaded_by_id: int,
    storage_key: str,
    content: bytes,
) -> Document:
    subject = Subject(
        school_id=school_id,
        name="Biology",
        slug=f"biology-{storage_key.replace('/', '-')}",
        description="Biology subject",
        is_active=True,
    )

    db_session.add(subject)
    await db_session.flush()

    save_document_bytes(
        storage_key,
        content,
    )

    document = Document(
        school_id=school_id,
        subject_id=subject.id,
        topic_id=None,
        uploaded_by_id=uploaded_by_id,
        title="Biology Notes",
        document_type=DocumentType.TEXTBOOK,
        form_level=1,
        academic_year=2026,
        exam_year=None,
        paper_number=None,
        original_filename="biology.txt",
        storage_key=storage_key,
        mime_type="text/plain",
        file_size=len(content),
        processing_status=DocumentProcessingStatus.UPLOADED,
        error_message=None,
        metadata_json=None,
        is_active=True,
    )

    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    return document


async def get_chunks(
    db_session,
    document_id: int,
) -> list[DocumentChunk]:
    result = await db_session.execute(
        select(DocumentChunk)
        .where(
            DocumentChunk.document_id == document_id,
        )
        .order_by(
            DocumentChunk.chunk_index.asc(),
        )
    )

    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_process_document_creates_chunks_and_marks_ready(
    db_session,
    seeded_users,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "DOCUMENT_STORAGE_PATH",
        str(tmp_path),
    )

    admin = seeded_users["admin"]
    school = seeded_users["school"]

    content = (
        "Photosynthesis allows green plants to make food "
        "using light energy. "
    ).encode("utf-8") * 40

    document = await create_document(
        db_session,
        school_id=school.id,
        uploaded_by_id=admin.id,
        storage_key="school-1/biology.txt",
        content=content,
    )

    result = await process_document(
        db_session,
        document.id,
        chunk_size=300,
        overlap=50,
    )

    await db_session.refresh(document)

    chunks = await get_chunks(
        db_session,
        document.id,
    )

    assert result["document_id"] == document.id
    assert result["chunk_count"] == len(chunks)
    assert len(chunks) > 1

    assert document.processing_status == (
        DocumentProcessingStatus.READY
    )
    assert document.error_message is None

    assert [
        chunk.chunk_index
        for chunk in chunks
    ] == list(range(len(chunks)))


@pytest.mark.asyncio
async def test_process_document_failure_marks_document_failed(
    db_session,
    seeded_users,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "DOCUMENT_STORAGE_PATH",
        str(tmp_path),
    )

    admin = seeded_users["admin"]
    school = seeded_users["school"]

    document = await create_document(
        db_session,
        school_id=school.id,
        uploaded_by_id=admin.id,
        storage_key="school-1/missing.txt",
        content=b"Temporary content",
    )

    stored_file = (
        Path(tmp_path)
        / document.storage_key
    )
    stored_file.unlink()

    with pytest.raises(
        FileNotFoundError,
        match="Stored document not found",
    ):
        await process_document(
            db_session,
            document.id,
        )

    await db_session.refresh(document)

    assert document.processing_status == (
        DocumentProcessingStatus.FAILED
    )
    assert document.error_message is not None
    assert "Stored document not found" in (
        document.error_message
    )

    chunks = await get_chunks(
        db_session,
        document.id,
    )

    assert chunks == []


@pytest.mark.asyncio
async def test_reprocessing_replaces_existing_chunks(
    db_session,
    seeded_users,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "DOCUMENT_STORAGE_PATH",
        str(tmp_path),
    )

    admin = seeded_users["admin"]
    school = seeded_users["school"]

    first_content = (
        "First version of the biology material. "
    ).encode("utf-8") * 50

    document = await create_document(
        db_session,
        school_id=school.id,
        uploaded_by_id=admin.id,
        storage_key="school-1/reprocess.txt",
        content=first_content,
    )

    await process_document(
        db_session,
        document.id,
        chunk_size=250,
        overlap=40,
    )

    first_chunks = await get_chunks(
        db_session,
        document.id,
    )

    assert len(first_chunks) > 1

    second_content = (
        b"Replacement material about cells and tissues."
    )

    save_document_bytes(
        document.storage_key,
        second_content,
    )

    await process_document(
        db_session,
        document.id,
        chunk_size=500,
        overlap=50,
    )

    second_chunks = await get_chunks(
        db_session,
        document.id,
    )

    assert len(second_chunks) == 1
    assert second_chunks[0].chunk_index == 0
    assert "Replacement material" in (
        second_chunks[0].content
    )
    assert "First version" not in (
        second_chunks[0].content
    )


@pytest.mark.asyncio
async def test_process_document_rejects_unknown_document(
    db_session,
):
    with pytest.raises(
        ValueError,
        match="Document not found",
    ):
        await process_document(
            db_session,
            999999,
        )
