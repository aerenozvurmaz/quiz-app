"""users join status columns

Revision ID: d4c1d84427df
Revises: 0b99b4e5b672
Create Date: 2025-08-13 08:35:30.328035

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4c1d84427df'
down_revision = '0b99b4e5b672'
branch_labels = None
depends_on = None


def upgrade():
    # 1) Create PG enum type FIRST (so column can use it)
    op.execute("CREATE TYPE join_status AS ENUM ('not_joined','joined','submitted')")

    # 2) Add columns (nullable first if you prefer backfilling)
    with op.batch_alter_table('users') as b:
        b.add_column(sa.Column('join_status', sa.Enum(name='join_status'), nullable=False, server_default='not_joined'))
        

    # 4) Optional backfill step (nothing to do; everyone starts not_joined with NULL quiz)

    # 5) Indexes
    # (You usually don’t need separate single‑column indexes if you have the composite one above.)

    # 6) Consistency check:
    # if not_joined -> current_quiz_id must be NULL
    # if joined/finished -> current_quiz_id must be NOT NULL

    # (Optional) keep the server_default for join_status/join_changed_at—handy going forward.


def downgrade():
    # Drop constraint + index + FK in reverse order
    op.drop_constraint("ck_users_join_status_consistent", "users", type_="check")

    with op.batch_alter_table('users') as b:
        b.drop_column('join_status')

    # Finally drop enum type
    op.execute("DROP TYPE join_status")
