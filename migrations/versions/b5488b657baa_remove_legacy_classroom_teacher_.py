"""remove legacy classroom teacher ownership

Revision ID: b5488b657baa
Revises: 3784e43340f3
Create Date: 2026-09-20 05:36:04.934353

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5488b657baa'
down_revision: Union[str, Sequence[str], None] = '3784e43340f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove legacy teacher ownership from classrooms."""
    op.drop_index(
        "ix_classrooms_teacher_id",
        table_name="classrooms",
    )
    op.drop_constraint(
        "fk_classrooms_teacher_id_users",
        "classrooms",
        type_="foreignkey",
    )
    op.drop_column(
        "classrooms",
        "teacher_id",
    )


def downgrade() -> None:
    """Restore legacy teacher ownership on classrooms."""
    op.add_column(
        "classrooms",
        sa.Column(
            "teacher_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_classrooms_teacher_id_users",
        "classrooms",
        "users",
        ["teacher_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_classrooms_teacher_id",
        "classrooms",
        ["teacher_id"],
        unique=False,
    )
