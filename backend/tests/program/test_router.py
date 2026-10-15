from fastapi.testclient import TestClient

from features.program.dto import PROGRAM_TEXT_MAX_LENGTH


class TestUpdateProgramRules:
    def test_本文が上限の文字数を超えると_422(self, client: TestClient) -> None:
        response = client.put("/api/programs/rules", json={"body": "あ" * (PROGRAM_TEXT_MAX_LENGTH + 1)})

        assert response.status_code == 422

    def test_本文が上限の文字数ちょうどなら保存できる(self, client: TestClient) -> None:
        body = "🏋" * PROGRAM_TEXT_MAX_LENGTH

        response = client.put("/api/programs/rules", json={"body": body})

        assert (response.status_code, response.json()["body"]) == (200, body)
