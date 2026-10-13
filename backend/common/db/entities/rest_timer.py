from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from common.db.entities.base import Base
from common.db.utc_datetime import UtcDateTime


class PushSubscriptionRow(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # endpoint の URL のパスは大文字と小文字を区別するトークンで、MySQL の既定の照合順序では別の端末が同じ行になる
    endpoint: Mapped[str] = mapped_column(
        String(500).with_variant(mysql.VARCHAR(500, collation="utf8mb4_0900_as_cs"), "mysql"),
        unique=True,
        nullable=False,
    )
    p256dh: Mapped[str] = mapped_column(String(128), nullable=False)
    auth: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=lambda: datetime.now(UTC))


class RestTimerRow(Base):
    __tablename__ = "rest_timers"
    __table_args__ = (CheckConstraint("slot = 1", name="ck_rest_timers_slot"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    slot: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, default=1)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    total_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    next_set_label: Mapped[str] = mapped_column(String(100), nullable=False)
