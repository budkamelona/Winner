import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class GiveawayStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    active = "active"
    finished = "finished"
    cancelled = "cancelled"


class FinishMode(str, enum.Enum):
    manual = "manual"
    by_time = "by_time"


class WinnerSelectionMode(str, enum.Enum):
    random = "random"
    manual = "manual"


class SelectionType(str, enum.Enum):
    random = "random"
    manual = "manual"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)

    channels: Mapped[list["Channel"]] = relationship("Channel", back_populates="owner")
    giveaways: Mapped[list["Giveaway"]] = relationship("Giveaway", back_populates="owner")


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("owner_user_id", "telegram_channel_id"),)

    owner: Mapped["User"] = relationship("User", back_populates="channels")
    giveaways: Mapped[list["Giveaway"]] = relationship("Giveaway", back_populates="channel")


class Giveaway(Base):
    __tablename__ = "giveaways"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("channels.id"), nullable=False)
    post_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    result_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    winners_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[GiveawayStatus] = mapped_column(
        Enum(GiveawayStatus, name="giveaway_status"), nullable=False, default=GiveawayStatus.draft
    )
    finish_mode: Mapped[FinishMode] = mapped_column(
        Enum(FinishMode, name="finish_mode"), nullable=False, default=FinishMode.manual
    )
    winner_selection_mode: Mapped[WinnerSelectionMode] = mapped_column(
        Enum(WinnerSelectionMode, name="winner_selection_mode"), nullable=False, default=WinnerSelectionMode.random
    )
    finish_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    publish_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    published_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    finished_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)

    owner: Mapped["User"] = relationship("User", back_populates="giveaways")
    channel: Mapped["Channel"] = relationship("Channel", back_populates="giveaways")
    participants: Mapped[list["GiveawayParticipant"]] = relationship("GiveawayParticipant", back_populates="giveaway")
    winners: Mapped[list["GiveawayWinner"]] = relationship("GiveawayWinner", back_populates="giveaway")
    captcha_challenges: Mapped[list["CaptchaChallenge"]] = relationship(
        "CaptchaChallenge", back_populates="giveaway"
    )


class GiveawayParticipant(Base):
    __tablename__ = "giveaway_participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    giveaway_id: Mapped[int] = mapped_column(Integer, ForeignKey("giveaways.id"), nullable=False)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    joined_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)
    is_captcha_passed: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (UniqueConstraint("giveaway_id", "telegram_user_id"),)

    giveaway: Mapped["Giveaway"] = relationship("Giveaway", back_populates="participants")


class GiveawayWinner(Base):
    __tablename__ = "giveaway_winners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    giveaway_id: Mapped[int] = mapped_column(Integer, ForeignKey("giveaways.id"), nullable=False)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    selection_type: Mapped[SelectionType] = mapped_column(
        Enum(SelectionType, name="selection_type"), nullable=False
    )
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)

    giveaway: Mapped["Giveaway"] = relationship("Giveaway", back_populates="winners")


class CaptchaChallenge(Base):
    __tablename__ = "captcha_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    giveaway_id: Mapped[int] = mapped_column(Integer, ForeignKey("giveaways.id"), nullable=False)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    question: Mapped[str] = mapped_column(String(255), nullable=False)
    correct_answer: Mapped[int] = mapped_column(Integer, nullable=False)
    wrong_answer_1: Mapped[int] = mapped_column(Integer, nullable=False)
    wrong_answer_2: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    is_solved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)

    giveaway: Mapped["Giveaway"] = relationship("Giveaway", back_populates="captcha_challenges")
