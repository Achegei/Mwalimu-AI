import re
from typing import Any

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.enrollment import Enrollment
from app.models.enums import (
    DocumentProcessingStatus,
    DocumentScope,
)
from app.models.teaching_assignment import TeachingAssignment


def _tokenize(text: str) -> list[str]:
    """
    Convert text into normalized search tokens.

    Short tokens are ignored because they provide little useful
    lexical relevance for document retrieval.
    """

    return [
        token
        for token in re.findall(
            r"[a-z0-9]+",
            text.lower(),
        )
        if len(token) >= 3
    ]


def _score_chunk(
    content: str,
    query_tokens: list[str],
) -> int:
    """
    Return a simple deterministic lexical relevance score.

    Each occurrence of a query token contributes to the score.
    """

    normalized_content = content.lower()

    return sum(
        normalized_content.count(token)
        for token in query_tokens
    )


async def retrieve_document_context(
    db: AsyncSession,
    *,
    school_id: int,
    subject_id: int,
    topic_id: int | None,
    form_level: int,
    query: str,
    student_id: int | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant chunks from active, successfully processed
    documents belonging to the requested school and curriculum scope.

    Tenant and curriculum boundaries are enforced in the database
    query before relevance ranking occurs.
    """

    if limit < 1:
        raise ValueError(
            "Retrieval limit must be at least 1."
        )

    cleaned_query = query.strip()

    if not cleaned_query:
        return []

    query_tokens = _tokenize(cleaned_query)

    if not query_tokens:
        return []

    statement = (
        select(
            DocumentChunk,
            Document,
        )
        .join(
            Document,
            DocumentChunk.document_id == Document.id,
        )
        .where(
            Document.school_id == school_id,
            Document.subject_id == subject_id,
            Document.form_level == form_level,
            Document.processing_status
            == DocumentProcessingStatus.READY,
            Document.is_active.is_(True),
        )
    )

    if topic_id is not None:
        statement = statement.where(
            Document.topic_id == topic_id,
        )

    # Authorization is enforced before relevance ranking.
    #
    # COMMON documents are available within their normal tenant and
    # curriculum scope. Assignment-scoped documents are available only
    # when the requesting student has an active enrollment in the
    # classroom represented by that active teaching assignment.
    if student_id is None:
        statement = statement.where(
            Document.scope == DocumentScope.COMMON,
        )
    else:
        authorized_assignment_document = exists(
            select(1)
            .select_from(TeachingAssignment)
            .join(
                Enrollment,
                Enrollment.classroom_id
                == TeachingAssignment.classroom_id,
            )
            .where(
                TeachingAssignment.id
                == Document.teaching_assignment_id,
                TeachingAssignment.school_id == school_id,
                TeachingAssignment.subject_id == subject_id,
                TeachingAssignment.is_active.is_(True),
                Enrollment.student_id == student_id,
                Enrollment.is_active.is_(True),
            )
        )

        statement = statement.where(
            or_(
                Document.scope == DocumentScope.COMMON,
                (
                    (
                        Document.scope
                        == DocumentScope.TEACHING_ASSIGNMENT
                    )
                    & authorized_assignment_document
                ),
            )
        )

    statement = statement.order_by(
        Document.id.asc(),
        DocumentChunk.chunk_index.asc(),
    )

    result = await db.execute(statement)

    ranked_results: list[
        tuple[int, DocumentChunk, Document]
    ] = []

    for chunk, document in result.all():
        score = _score_chunk(
            chunk.content,
            query_tokens,
        )

        if score <= 0:
            continue

        ranked_results.append(
            (
                score,
                chunk,
                document,
            )
        )

    ranked_results.sort(
        key=lambda item: (
            -item[0],
            item[2].id,
            item[1].chunk_index,
        )
    )

    context_results: list[dict[str, Any]] = []

    for score, chunk, document in ranked_results[:limit]:
        context_results.append(
            {
                "document_id": document.id,
                "document_title": document.title,
                "document_type": (
                    document.document_type.value
                ),
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "content": chunk.content,
                "score": score,
            }
        )

    return context_results
