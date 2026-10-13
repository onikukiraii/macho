from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from common.db.entities import UserRow
from common.errors import Conflict
from features.user.repository import DbUserRepository


class TestListAll:
    def test_空なら空リスト(self, db_session: Session) -> None:
        assert DbUserRepository(db_session).list_all() == []

    def test_id_昇順で返す(self, db_session: Session, create_user: Callable[..., UserRow]) -> None:
        create_user(name="田中太郎", email="tanaka@example.com")
        create_user(name="鈴木花子", email="suzuki@example.com")

        assert [user.name for user in DbUserRepository(db_session).list_all()] == ["田中太郎", "鈴木花子"]


class TestCreate:
    def test_作成した行をドメイン型で返す(self, db_session: Session) -> None:
        user = DbUserRepository(db_session).create(name="田中太郎", email="tanaka@example.com")

        assert user.id > 0
        assert user.name == "田中太郎"
        assert user.created_at is not None

    def test_email_が重複したら_Conflict(self, db_session: Session, create_user: Callable[..., UserRow]) -> None:
        create_user(email="dup@example.com")

        with pytest.raises(Conflict):
            DbUserRepository(db_session).create(name="重複", email="dup@example.com")
