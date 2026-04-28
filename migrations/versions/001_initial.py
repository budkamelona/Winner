"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_user_id"),
    )
    op.create_index("ix_users_telegram_user_id", "users", ["telegram_user_id"])

    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_channel_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", "telegram_channel_id"),
    )

    op.create_table(
        "giveaways",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("post_message_id", sa.BigInteger(), nullable=True),
        sa.Column("result_message_id", sa.BigInteger(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("winners_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.Enum("draft", "scheduled", "active", "finished", "cancelled", name="giveaway_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "finish_mode",
            sa.Enum("manual", "by_time", name="finish_mode"),
            nullable=False,
            server_default="manual",
        ),
        sa.Column(
            "winner_selection_mode",
            sa.Enum("random", "manual", name="winner_selection_mode"),
            nullable=False,
            server_default="random",
        ),
        sa.Column("finish_at_utc", sa.DateTime(), nullable=True),
        sa.Column("publish_at_utc", sa.DateTime(), nullable=True),
        sa.Column("published_at_utc", sa.DateTime(), nullable=True),
        sa.Column("finished_at_utc", sa.DateTime(), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "giveaway_participants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("giveaway_id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("joined_at_utc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("is_captcha_passed", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["giveaway_id"], ["giveaways.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("giveaway_id", "telegram_user_id"),
    )

    op.create_table(
        "giveaway_winners",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("giveaway_id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column(
            "selection_type",
            sa.Enum("random", "manual", name="selection_type"),
            nullable=False,
        ),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["giveaway_id"], ["giveaways.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "captcha_challenges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("giveaway_id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("question", sa.String(255), nullable=False),
        sa.Column("correct_answer", sa.Integer(), nullable=False),
        sa.Column("wrong_answer_1", sa.Integer(), nullable=False),
        sa.Column("wrong_answer_2", sa.Integer(), nullable=False),
        sa.Column("expires_at_utc", sa.DateTime(), nullable=False),
        sa.Column("is_solved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at_utc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["giveaway_id"], ["giveaways.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("captcha_challenges")
    op.drop_table("giveaway_winners")
    op.drop_table("giveaway_participants")
    op.drop_table("giveaways")
    op.drop_table("channels")
    op.drop_index("ix_users_telegram_user_id", "users")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS giveaway_status")
    op.execute("DROP TYPE IF EXISTS finish_mode")
    op.execute("DROP TYPE IF EXISTS winner_selection_mode")
    op.execute("DROP TYPE IF EXISTS selection_type")
