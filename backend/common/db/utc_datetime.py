from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, TypeDecorator
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeEngine


class UtcDateTime(TypeDecorator[datetime]):
    """UTC で保存し、aware な datetime で返す。MySQL ではマイクロ秒まで保持する。"""

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "mysql":
            return dialect.type_descriptor(mysql.DATETIME(fsp=6))
        return dialect.type_descriptor(DateTime())

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive な datetime は書き込めません")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)
