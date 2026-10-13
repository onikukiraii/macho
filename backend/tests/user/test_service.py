import pytest

from common.errors import BusinessRuleViolation, Conflict
from features.user.service import create_user, list_users
from tests.fakes import InMemoryUserRepository


class TestListUsers:
    def test_登録順に返す(self) -> None:
        repo = InMemoryUserRepository()
        repo.create(name="田中太郎", email="tanaka@example.com")
        repo.create(name="鈴木花子", email="suzuki@example.com")

        assert [user.name for user in list_users(repo)] == ["田中太郎", "鈴木花子"]


class TestCreateUser:
    def test_email_を正規化して保存する(self) -> None:
        repo = InMemoryUserRepository()

        user = create_user(repo, name="田中太郎", email="Tanaka@Example.com")

        assert user.email == "tanaka@example.com"

    def test_名前が空なら弾く(self) -> None:
        repo = InMemoryUserRepository()

        with pytest.raises(BusinessRuleViolation):
            create_user(repo, name="  ", email="tanaka@example.com")

        assert repo.users == []

    def test_大文字違いの重複も衝突として弾く(self) -> None:
        repo = InMemoryUserRepository()
        create_user(repo, name="田中太郎", email="tanaka@example.com")

        with pytest.raises(Conflict):
            create_user(repo, name="別人", email="TANAKA@example.com")
