"""make subjects school owned

Revision ID: 8232513eeb72
Revises: e9f58effb51f
Create Date: 2026-09-13 16:12:05.500903

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8232513eeb72'
down_revision: Union[str, Sequence[str], None] = 'e9f58effb51f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make subjects school-owned without losing existing data."""

    # 1. Add the ownership column as nullable first so existing
    # subject rows remain valid during the migration.
    op.add_column(
        "subjects",
        sa.Column(
            "school_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    # 2. Add the school foreign key and supporting index.
    op.create_foreign_key(
        op.f("fk_subjects_school_id_schools"),
        "subjects",
        "schools",
        ["school_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index(
        op.f("ix_subjects_school_id"),
        "subjects",
        ["school_id"],
        unique=False,
    )

    # 3. Existing Mwalimu AI data used global subjects.
    #
    # If subjects already exist, ownership can only be inferred
    # safely when exactly one school exists. Refuse to guess when
    # multiple schools are present.
    connection = op.get_bind()

    subject_count = connection.execute(
        sa.text(
            "SELECT COUNT(*) "
            "FROM subjects"
        )
    ).scalar_one()

    if subject_count:
        school_ids = [
            row[0]
            for row in connection.execute(
                sa.text(
                    "SELECT id "
                    "FROM schools "
                    "ORDER BY id"
                )
            ).all()
        ]

        if len(school_ids) != 1:
            raise RuntimeError(
                "Cannot safely migrate global subjects to "
                "school ownership: existing subjects were found "
                f"but the database contains {len(school_ids)} schools. "
                "Assign subject ownership explicitly before retrying."
            )

        connection.execute(
            sa.text(
                "UPDATE subjects "
                "SET school_id = :school_id "
                "WHERE school_id IS NULL"
            ),
            {"school_id": school_ids[0]},
        )

    # 4. Once all existing rows are owned by a school,
    # enforce mandatory ownership.
    op.alter_column(
        "subjects",
        "school_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # 5. A subject slug is no longer globally unique.
    # Each school gets its own subject namespace.
    op.drop_index(
        op.f("ix_subjects_slug"),
        table_name="subjects",
    )

    op.create_index(
        op.f("ix_subjects_slug"),
        "subjects",
        ["slug"],
        unique=False,
    )

    op.create_unique_constraint(
        "uq_subject_school_slug",
        "subjects",
        ["school_id", "slug"],
    )


def downgrade() -> None:
    """Restore global subjects if doing so is unambiguous."""

    connection = op.get_bind()

    duplicate_slug = connection.execute(
        sa.text(
            """
            SELECT slug
            FROM subjects
            GROUP BY slug
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).scalar_one_or_none()

    if duplicate_slug is not None:
        raise RuntimeError(
            "Cannot downgrade subjects to global ownership because "
            f"the slug {duplicate_slug!r} exists in more than one school."
        )

    op.drop_constraint(
        "uq_subject_school_slug",
        "subjects",
        type_="unique",
    )

    op.drop_index(
        op.f("ix_subjects_school_id"),
        table_name="subjects",
    )

    op.drop_constraint(
        op.f("fk_subjects_school_id_schools"),
        "subjects",
        type_="foreignkey",
    )

    op.drop_index(
        op.f("ix_subjects_slug"),
        table_name="subjects",
    )

    op.create_index(
        op.f("ix_subjects_slug"),
        "subjects",
        ["slug"],
        unique=True,
    )

    op.drop_column(
        "subjects",
        "school_id",
    )
