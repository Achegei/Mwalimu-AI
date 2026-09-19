import pytest

from app.models.content import Subject, Topic
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.enums import (
    DocumentProcessingStatus,
    DocumentType,
)
from app.models.school import School
from app.services.document_retrieval import (
    retrieve_document_context,
)


async def create_document_with_chunks(
    db_session,
    *,
    school_id: int,
    subject_id: int,
    topic_id: int | None,
    form_level: int,
    title: str,
    contents: list[str],
    processing_status: DocumentProcessingStatus = (
        DocumentProcessingStatus.READY
    ),
    is_active: bool = True,
) -> Document:
    document = Document(
        school_id=school_id,
        subject_id=subject_id,
        topic_id=topic_id,
        uploaded_by_id=None,
        title=title,
        document_type=DocumentType.TEXTBOOK,
        form_level=form_level,
        academic_year=None,
        exam_year=None,
        paper_number=None,
        original_filename=f"{title.lower().replace(' ', '-')}.txt",
        storage_key=f"tests/{school_id}/{title.lower().replace(' ', '-')}.txt",
        mime_type="text/plain",
        file_size=sum(
            len(content.encode("utf-8"))
            for content in contents
        ),
        processing_status=processing_status,
        error_message=None,
        metadata_json=None,
        is_active=is_active,
    )

    db_session.add(document)
    await db_session.flush()

    for index, content in enumerate(contents):
        db_session.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=content,
                page_number=index + 1,
                character_count=len(content),
                metadata_json=None,
            )
        )

    await db_session.commit()

    return document


@pytest.mark.asyncio
async def test_retrieval_returns_matching_ready_chunk(
    db_session,
    seeded_users,
):
    school = seeded_users["school"]

    subject = Subject(
        school_id=school.id,
        name="Biology",
        slug="retrieval-biology",
        description=None,
        is_active=True,
    )
    db_session.add(subject)
    await db_session.flush()

    topic = Topic(
        subject_id=subject.id,
        slug="retrieval-photosynthesis",
        title="Photosynthesis",
        summary="How green plants make food.",
        form_level=2,
        order_index=1,
        is_active=True,
    )
    db_session.add(topic)
    await db_session.flush()

    await create_document_with_chunks(
        db_session,
        school_id=school.id,
        subject_id=subject.id,
        topic_id=topic.id,
        form_level=2,
        title="Biology Textbook",
        contents=[
            (
                "Photosynthesis uses light energy to make "
                "food in green plants."
            ),
            (
                "Respiration releases energy from food "
                "inside living cells."
            ),
        ],
    )

    results = await retrieve_document_context(
        db=db_session,
        school_id=school.id,
        subject_id=subject.id,
        topic_id=topic.id,
        form_level=2,
        query="How does photosynthesis use light energy?",
        limit=5,
    )

    assert results
    assert "Photosynthesis" in results[0]["content"]
    assert results[0]["document_title"] == "Biology Textbook"
    assert results[0]["page_number"] == 1


@pytest.mark.asyncio
async def test_retrieval_never_returns_other_school_chunks(
    db_session,
    seeded_users,
):
    own_school = seeded_users["school"]

    own_subject = Subject(
        school_id=own_school.id,
        name="Biology",
        slug="own-retrieval-biology",
        description=None,
        is_active=True,
    )
    db_session.add(own_subject)
    await db_session.flush()

    own_topic = Topic(
        subject_id=own_subject.id,
        slug="own-retrieval-respiration",
        title="Respiration",
        summary=None,
        form_level=2,
        order_index=1,
        is_active=True,
    )
    db_session.add(own_topic)
    await db_session.flush()

    await create_document_with_chunks(
        db_session,
        school_id=own_school.id,
        subject_id=own_subject.id,
        topic_id=own_topic.id,
        form_level=2,
        title="Own Biology",
        contents=[
            "Respiration releases energy from glucose.",
        ],
    )

    foreign_school = School(
        name="Foreign Retrieval School",
        code="RETRIEVAL-FOREIGN",
        is_active=True,
    )
    db_session.add(foreign_school)
    await db_session.flush()

    foreign_subject = Subject(
        school_id=foreign_school.id,
        name="Biology",
        slug="foreign-retrieval-biology",
        description=None,
        is_active=True,
    )
    db_session.add(foreign_subject)
    await db_session.flush()

    foreign_topic = Topic(
        subject_id=foreign_subject.id,
        slug="foreign-retrieval-respiration",
        title="Respiration",
        summary=None,
        form_level=2,
        order_index=1,
        is_active=True,
    )
    db_session.add(foreign_topic)
    await db_session.flush()

    foreign_document = await create_document_with_chunks(
        db_session,
        school_id=foreign_school.id,
        subject_id=foreign_subject.id,
        topic_id=foreign_topic.id,
        form_level=2,
        title="Foreign Biology",
        contents=[
            (
                "Respiration releases energy from glucose. "
                "FOREIGN SCHOOL SECRET CONTENT."
            ),
        ],
    )

    results = await retrieve_document_context(
        db=db_session,
        school_id=own_school.id,
        subject_id=own_subject.id,
        topic_id=own_topic.id,
        form_level=2,
        query="respiration glucose energy",
        limit=10,
    )

    assert results

    document_ids = {
        result["document_id"]
        for result in results
    }

    assert foreign_document.id not in document_ids

    assert all(
        "FOREIGN SCHOOL SECRET CONTENT"
        not in result["content"]
        for result in results
    )


@pytest.mark.asyncio
async def test_retrieval_excludes_non_ready_documents(
    db_session,
    seeded_users,
):
    school = seeded_users["school"]

    subject = Subject(
        school_id=school.id,
        name="Chemistry",
        slug="retrieval-chemistry",
        description=None,
        is_active=True,
    )
    db_session.add(subject)
    await db_session.flush()

    topic = Topic(
        subject_id=subject.id,
        slug="retrieval-acids",
        title="Acids",
        summary=None,
        form_level=2,
        order_index=1,
        is_active=True,
    )
    db_session.add(topic)
    await db_session.flush()

    failed_document = await create_document_with_chunks(
        db_session,
        school_id=school.id,
        subject_id=subject.id,
        topic_id=topic.id,
        form_level=2,
        title="Failed Chemistry",
        contents=[
            "Hydrochloric acid contains hydrogen ions.",
        ],
        processing_status=(
            DocumentProcessingStatus.FAILED
        ),
    )

    results = await retrieve_document_context(
        db=db_session,
        school_id=school.id,
        subject_id=subject.id,
        topic_id=topic.id,
        form_level=2,
        query="hydrochloric acid hydrogen ions",
        limit=5,
    )

    assert all(
        result["document_id"] != failed_document.id
        for result in results
    )


@pytest.mark.asyncio
async def test_retrieval_excludes_inactive_documents(
    db_session,
    seeded_users,
):
    school = seeded_users["school"]

    subject = Subject(
        school_id=school.id,
        name="Physics",
        slug="retrieval-physics",
        description=None,
        is_active=True,
    )
    db_session.add(subject)
    await db_session.flush()

    topic = Topic(
        subject_id=subject.id,
        slug="retrieval-force",
        title="Force",
        summary=None,
        form_level=2,
        order_index=1,
        is_active=True,
    )
    db_session.add(topic)
    await db_session.flush()

    inactive_document = await create_document_with_chunks(
        db_session,
        school_id=school.id,
        subject_id=subject.id,
        topic_id=topic.id,
        form_level=2,
        title="Inactive Physics",
        contents=[
            "Force can change the motion of an object.",
        ],
        is_active=False,
    )

    results = await retrieve_document_context(
        db=db_session,
        school_id=school.id,
        subject_id=subject.id,
        topic_id=topic.id,
        form_level=2,
        query="force motion object",
        limit=5,
    )

    assert all(
        result["document_id"] != inactive_document.id
        for result in results
    )


@pytest.mark.asyncio
async def test_retrieval_respects_subject_topic_and_form_scope(
    db_session,
    seeded_users,
):
    school = seeded_users["school"]

    biology = Subject(
        school_id=school.id,
        name="Biology",
        slug="scope-biology",
        description=None,
        is_active=True,
    )
    chemistry = Subject(
        school_id=school.id,
        name="Chemistry",
        slug="scope-chemistry",
        description=None,
        is_active=True,
    )

    db_session.add_all([biology, chemistry])
    await db_session.flush()

    biology_topic = Topic(
        subject_id=biology.id,
        slug="scope-cells",
        title="Cells",
        summary=None,
        form_level=2,
        order_index=1,
        is_active=True,
    )
    chemistry_topic = Topic(
        subject_id=chemistry.id,
        slug="scope-chemistry-cells",
        title="Chemistry Cells",
        summary=None,
        form_level=2,
        order_index=1,
        is_active=True,
    )

    db_session.add_all(
        [
            biology_topic,
            chemistry_topic,
        ]
    )
    await db_session.flush()

    expected_document = await create_document_with_chunks(
        db_session,
        school_id=school.id,
        subject_id=biology.id,
        topic_id=biology_topic.id,
        form_level=2,
        title="Correct Scope",
        contents=[
            "Cells contain structures with specific functions.",
        ],
    )

    await create_document_with_chunks(
        db_session,
        school_id=school.id,
        subject_id=chemistry.id,
        topic_id=chemistry_topic.id,
        form_level=2,
        title="Wrong Subject",
        contents=[
            "Cells contain structures with specific functions.",
        ],
    )

    await create_document_with_chunks(
        db_session,
        school_id=school.id,
        subject_id=biology.id,
        topic_id=biology_topic.id,
        form_level=3,
        title="Wrong Form",
        contents=[
            "Cells contain structures with specific functions.",
        ],
    )

    results = await retrieve_document_context(
        db=db_session,
        school_id=school.id,
        subject_id=biology.id,
        topic_id=biology_topic.id,
        form_level=2,
        query="cells structures functions",
        limit=10,
    )

    assert results

    document_ids = {
        result["document_id"]
        for result in results
    }

    assert document_ids == {
        expected_document.id,
    }


@pytest.mark.asyncio
async def test_retrieval_respects_limit(
    db_session,
    seeded_users,
):
    school = seeded_users["school"]

    subject = Subject(
        school_id=school.id,
        name="Geography",
        slug="retrieval-geography",
        description=None,
        is_active=True,
    )
    db_session.add(subject)
    await db_session.flush()

    topic = Topic(
        subject_id=subject.id,
        slug="retrieval-rivers",
        title="Rivers",
        summary=None,
        form_level=2,
        order_index=1,
        is_active=True,
    )
    db_session.add(topic)
    await db_session.flush()

    await create_document_with_chunks(
        db_session,
        school_id=school.id,
        subject_id=subject.id,
        topic_id=topic.id,
        form_level=2,
        title="River Notes",
        contents=[
            "River erosion shapes valleys.",
            "River erosion transports material.",
            "River erosion can create waterfalls.",
        ],
    )

    results = await retrieve_document_context(
        db=db_session,
        school_id=school.id,
        subject_id=subject.id,
        topic_id=topic.id,
        form_level=2,
        query="river erosion",
        limit=2,
    )

    assert len(results) == 2


@pytest.mark.asyncio
async def test_retrieval_rejects_invalid_limit(
    db_session,
    seeded_users,
):
    school = seeded_users["school"]

    with pytest.raises(
        ValueError,
        match="limit",
    ):
        await retrieve_document_context(
            db=db_session,
            school_id=school.id,
            subject_id=1,
            topic_id=1,
            form_level=2,
            query="test",
            limit=0,
        )


@pytest.mark.asyncio
async def test_retrieval_empty_query_returns_no_results(
    db_session,
    seeded_users,
):
    school = seeded_users["school"]

    results = await retrieve_document_context(
        db=db_session,
        school_id=school.id,
        subject_id=1,
        topic_id=1,
        form_level=2,
        query="   ",
        limit=5,
    )

    assert results == []


@pytest.mark.asyncio
async def test_retrieval_short_tokens_return_no_results(
    db_session,
    seeded_users,
):
    school = seeded_users["school"]

    results = await retrieve_document_context(
        db=db_session,
        school_id=school.id,
        subject_id=1,
        topic_id=1,
        form_level=2,
        query="a an to of",
        limit=5,
    )

    assert results == []


@pytest.mark.asyncio
async def test_retrieval_excludes_irrelevant_chunks(
    db_session,
    seeded_users,
):
    school = seeded_users["school"]

    subject = Subject(
        school_id=school.id,
        name="Agriculture",
        slug="retrieval-agriculture",
        description=None,
        is_active=True,
    )
    db_session.add(subject)
    await db_session.flush()

    topic = Topic(
        subject_id=subject.id,
        slug="retrieval-soil",
        title="Soil",
        summary=None,
        form_level=2,
        order_index=1,
        is_active=True,
    )
    db_session.add(topic)
    await db_session.flush()

    await create_document_with_chunks(
        db_session,
        school_id=school.id,
        subject_id=subject.id,
        topic_id=topic.id,
        form_level=2,
        title="Agriculture Notes",
        contents=[
            "Soil erosion can remove fertile topsoil.",
            "Dairy cattle require balanced nutrition.",
        ],
    )

    results = await retrieve_document_context(
        db=db_session,
        school_id=school.id,
        subject_id=subject.id,
        topic_id=topic.id,
        form_level=2,
        query="soil erosion topsoil",
        limit=10,
    )

    assert len(results) == 1
    assert "Soil erosion" in results[0]["content"]


@pytest.mark.asyncio
async def test_retrieval_excludes_other_topic_in_same_subject(
    db_session,
    seeded_users,
):
    school = seeded_users["school"]

    subject = Subject(
        school_id=school.id,
        name="History",
        slug="retrieval-history",
        description=None,
        is_active=True,
    )
    db_session.add(subject)
    await db_session.flush()

    target_topic = Topic(
        subject_id=subject.id,
        slug="retrieval-trade",
        title="Trade",
        summary=None,
        form_level=2,
        order_index=1,
        is_active=True,
    )

    other_topic = Topic(
        subject_id=subject.id,
        slug="retrieval-government",
        title="Government",
        summary=None,
        form_level=2,
        order_index=2,
        is_active=True,
    )

    db_session.add_all(
        [
            target_topic,
            other_topic,
        ]
    )
    await db_session.flush()

    target_document = await create_document_with_chunks(
        db_session,
        school_id=school.id,
        subject_id=subject.id,
        topic_id=target_topic.id,
        form_level=2,
        title="Trade Notes",
        contents=[
            "Trade involved exchange of goods between communities.",
        ],
    )

    other_document = await create_document_with_chunks(
        db_session,
        school_id=school.id,
        subject_id=subject.id,
        topic_id=other_topic.id,
        form_level=2,
        title="Government Notes",
        contents=[
            (
                "Trade and exchange were sometimes regulated "
                "by systems of government."
            ),
        ],
    )

    results = await retrieve_document_context(
        db=db_session,
        school_id=school.id,
        subject_id=subject.id,
        topic_id=target_topic.id,
        form_level=2,
        query="trade exchange",
        limit=10,
    )

    document_ids = {
        result["document_id"]
        for result in results
    }

    assert target_document.id in document_ids
    assert other_document.id not in document_ids


@pytest.mark.asyncio
async def test_retrieval_ranks_stronger_match_first(
    db_session,
    seeded_users,
):
    school = seeded_users["school"]

    subject = Subject(
        school_id=school.id,
        name="Business Studies",
        slug="retrieval-business",
        description=None,
        is_active=True,
    )
    db_session.add(subject)
    await db_session.flush()

    topic = Topic(
        subject_id=subject.id,
        slug="retrieval-demand",
        title="Demand",
        summary=None,
        form_level=2,
        order_index=1,
        is_active=True,
    )
    db_session.add(topic)
    await db_session.flush()

    await create_document_with_chunks(
        db_session,
        school_id=school.id,
        subject_id=subject.id,
        topic_id=topic.id,
        form_level=2,
        title="Demand Notes",
        contents=[
            "Demand refers to willingness to buy a product.",
            (
                "Demand changes when consumer income changes. "
                "Demand can also change because of price. "
                "Consumer demand is influenced by preferences."
            ),
        ],
    )

    results = await retrieve_document_context(
        db=db_session,
        school_id=school.id,
        subject_id=subject.id,
        topic_id=topic.id,
        form_level=2,
        query="demand consumer price",
        limit=5,
    )

    assert len(results) == 2

    assert results[0]["score"] > results[1]["score"]

    assert "Consumer demand" in results[0]["content"]
