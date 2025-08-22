"""user_status

Revision ID: 1fb44e1e4e6e
Revises: 5cd5770512f1
Create Date: 2025-08-19 15:29:25.466941
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1fb44e1e4e6e"
down_revision = "5cd5770512f1"
branch_labels = None
depends_on = None


def upgrade():
    # Normalize/ensure enum type
    op.execute("""
    DO $$ BEGIN
      -- If someone created a type with a hyphen in the past, rename it
      IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user-status') THEN
        ALTER TYPE "user-status" RENAME TO user_status;
      END IF;
    END $$;
    """)
    op.execute("""
    DO $$ BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_status') THEN
        CREATE TYPE user_status AS ENUM ('normal','warned','banned');
      END IF;
    END $$;
    """)

    # quiz_submission: action_time, user_status_at_action
    with op.batch_alter_table("quiz_submission", schema=None) as batch_op:
        batch_op.add_column(sa.Column("action_time", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column(
            "user_status_at_action",
            sa.Enum("normal", "warned", "banned", name="user_status"),
            nullable=True,
        ))
        batch_op.create_index("ix_quiz_submission_action_time", ["action_time"], unique=False)
        batch_op.create_index(
            "ix_quiz_submission_user_status_at_action",
            ["user_status_at_action"],
            unique=False,
        )

    # users: user_status, timeout, timeout_until
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            "user_status",
            sa.Enum("normal", "warned", "banned", name="user_status"),
            nullable=False,
            server_default="normal",
        ))
        batch_op.add_column(sa.Column(
            "timeout",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ))
        batch_op.add_column(sa.Column("timeout_until", sa.DateTime(timezone=True), nullable=True))

        batch_op.create_index("ix_users_user_status", ["user_status"], unique=False)
        batch_op.create_index("ix_users_timeout", ["timeout"], unique=False)
        batch_op.create_index("ix_users_timeout_until", ["timeout_until"], unique=False)


def downgrade():
    # Drop users cols/indexes
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index("ix_users_timeout_until")
        batch_op.drop_index("ix_users_timeout")
        batch_op.drop_index("ix_users_user_status")
        batch_op.drop_column("timeout_until")
        batch_op.drop_column("timeout")
        batch_op.drop_column("user_status")

    # Drop quiz_submission cols/indexes
    with op.batch_alter_table("quiz_submission", schema=None) as batch_op:
        batch_op.drop_index("ix_quiz_submission_user_status")
        batch_op.drop_index("ix_quiz_submission_action_time")
        batch_op.drop_column("user_status_at_action")
        batch_op.drop_column("action_time")

    # Finally, drop enum type if no longer referenced
    op.execute("DROP TYPE IF EXISTS user_status")
