"""submission logic

Revision ID: ae6a146e75d2
Revises: d4c1d84427df
Create Date: 2025-08-13 12:32:00.947472

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ae6a146e75d2'
down_revision = 'd4c1d84427df'
branch_labels = None
depends_on = None


def upgrade():
    from alembic import op
    import sqlalchemy as sa

    # submitted_at: drop default, make nullable
    with op.batch_alter_table("quiz_submission") as b:
        b.alter_column("submitted_at",
                       existing_type=sa.DateTime(timezone=True),
                       server_default=None,
                       nullable=True)

        # answers default {}
        b.alter_column("answers",
                       existing_type=sa.dialects.postgresql.JSONB(),
                       server_default=sa.text("'{}'::jsonb"),
                       nullable=False)

        # score default 0
        b.alter_column("score",
                       existing_type=sa.Integer(),
                       server_default="0",
                       nullable=False)

def downgrade():
    from alembic import op
    import sqlalchemy as sa
    with op.batch_alter_table("quiz_submission") as b:
        # revert as you had before (submitted_at default NOW(); adjust if needed)
        b.alter_column("score", server_default=None, nullable=False)
        b.alter_column("answers", server_default=None, nullable=False)
        b.alter_column("submitted_at",
                       server_default=sa.text("NOW()"),
                       nullable=True)

