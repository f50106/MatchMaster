"""add resume_file_name to evaluations

Revision ID: b7c8d9e0f1a2
Revises: ef084b2f1d45
Create Date: 2026-03-20 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = 'ef084b2f1d45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'evaluations',
        sa.Column('resume_file_name', sa.String(length=500), nullable=False, server_default=''),
    )


def downgrade() -> None:
    op.drop_column('evaluations', 'resume_file_name')
