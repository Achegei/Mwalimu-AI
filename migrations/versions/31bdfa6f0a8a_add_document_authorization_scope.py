"""add document authorization scope

Revision ID: 31bdfa6f0a8a
Revises: b5488b657baa
Create Date: 2026-09-20 05:47:27.459468

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "31bdfa6f0a8a"
down_revision: Union[str, Sequence[str], None] = "b5488b657baa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


document_scope = postgresql.ENUM(
    "common",
    "teaching_assignment",
    name="document_scope",
    create_type=False,
)


def upgrade() -> None:
    """Add explicit authorization scope to documents."""

    # Create the PostgreSQL enum explicitly so migration ordering
    # remains deterministic.
    document_scope.create(
        op.get_bind(),
        checkfirst=True,
    )

    # Scope starts nullable so existing document rows can be
    # backfilled safely before the NOT NULL invariant is applied.
    op.add_column(
        "documents",
        sa.Column(
            "scope",
            document_scope,
            nullable=True,
        ),
    )

    op.add_column(
        "documents",
        sa.Column(
            "teaching_assignment_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    # Every document that existed before assignment-specific
    # document ownership was introduced is common school material.
    op.execute(
        sa.text(
            """
            UPDATE documents
            SET scope = 'common'
            WHERE scope IS NULL
            """
        )
    )

    op.alter_column(
        "documents",
        "scope",
        existing_type=document_scope,
        nullable=False,
    )

    op.create_foreign_key(
        "fk_documents_teaching_assignment_id_teaching_assignments",
        "documents",
        "teaching_assignments",
        ["teaching_assignment_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index(
        "ix_documents_scope",
        "documents",
        ["scope"],
        unique=False,
    )

    op.create_index(
        "ix_documents_teaching_assignment_id",
        "documents",
        ["teaching_assignment_id"],
        unique=False,
    )

    # Persistence invariant:
    #
    # COMMON documents cannot belong to a teaching assignment.
    # TEACHING_ASSIGNMENT documents must belong to one.
    op.create_check_constraint(
        "scope_teaching_assignment",
        "documents",
        """
        (
            scope = 'common'
            AND teaching_assignment_id IS NULL
        )
        OR
        (
            scope = 'teaching_assignment'
            AND teaching_assignment_id IS NOT NULL
        )
        """,
    )


def downgrade() -> None:
    """Remove explicit document authorization scope."""

    op.drop_constraint(
        "scope_teaching_assignment",
        "documents",
        type_="check",
    )

    op.drop_index(
        "ix_documents_teaching_assignment_id",
        table_name="documents",
    )

    op.drop_index(
        "ix_documents_scope",
        table_name="documents",
    )

    op.drop_constraint(
        "fk_documents_teaching_assignment_id_teaching_assignments",
        "documents",
        type_="foreignkey",
    )

    op.drop_column(
        "documents",
        "teaching_assignment_id",
    )

    op.drop_column(
        "documents",
        "scope",
    )

    document_scope.drop(
        op.get_bind(),
        checkfirst=True,
    )
