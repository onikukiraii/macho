from collections.abc import Callable

from fastapi.testclient import TestClient

from common.db.entities import UserRow


class TestGetUsers:
    def test_空なら空配列(self, client: TestClient) -> None:
        resp = client.get("/users/")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_登録順に返す(self, client: TestClient, create_user: Callable[..., UserRow]) -> None:
        create_user(name="田中太郎", email="tanaka@example.com")
        create_user(name="鈴木花子", email="suzuki@example.com")

        resp = client.get("/users/")

        assert resp.status_code == 200
        assert [user["name"] for user in resp.json()] == ["田中太郎", "鈴木花子"]


class TestCreateUser:
    def test_作成できる(self, client: TestClient) -> None:
        resp = client.post("/users/", json={"name": "新規ユーザー", "email": "new@example.com"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "新規ユーザー"
        assert body["email"] == "new@example.com"
        assert body["id"] > 0

    def test_email_が重複したら_409(self, client: TestClient, create_user: Callable[..., UserRow]) -> None:
        create_user(email="dup@example.com")

        resp = client.post("/users/", json={"name": "重複", "email": "dup@example.com"})

        assert resp.status_code == 409

    def test_名前が空白だけなら_400(self, client: TestClient) -> None:
        resp = client.post("/users/", json={"name": "   ", "email": "blank@example.com"})

        assert resp.status_code == 400
