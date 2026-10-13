from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import create_app

INDEX_HTML = "<html><body>macho</body></html>"
APP_JS = "console.log('macho');"
SECRET = "outside-dist-secret"


@pytest.fixture()
def dist_client(tmp_path: Path) -> TestClient:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX_HTML)
    (dist / "assets" / "app.js").write_text(APP_JS)
    (tmp_path / "secret.txt").write_text(SECRET)
    return TestClient(create_app(frontend_dist_dir=dist))


class TestCreateApp:
    def test_画面の_URL_を直接開くと_index_html_を返す(self, dist_client: TestClient) -> None:
        resp = dist_client.get("/exercises/abc")

        assert resp.status_code == 200
        assert resp.text == INDEX_HTML

    def test_dist_の中の実ファイルは中身と_content_type_で返す(self, dist_client: TestClient) -> None:
        resp = dist_client.get("/assets/app.js")

        assert resp.status_code == 200
        assert resp.text == APP_JS
        assert "javascript" in resp.headers["content-type"]

    def test_api_の未知のパスは_JSON_の_404_を返す(self, dist_client: TestClient) -> None:
        resp = dist_client.get("/api/unknown")

        assert resp.status_code == 404
        assert resp.headers["content-type"].startswith("application/json")
        assert resp.json() == {"detail": "Not Found"}

    @pytest.mark.parametrize(
        "path",
        [
            "/%2e%2e/secret.txt",
            "/assets/%2e%2e/%2e%2e/secret.txt",
            "/..%2fsecret.txt",
            "/assets/..%2f..%2fsecret.txt",
        ],
    )
    def test_dist_の外のファイルは返さず_index_html_を返す(self, dist_client: TestClient, path: str) -> None:
        resp = dist_client.get(path)

        assert resp.status_code == 200
        assert resp.text == INDEX_HTML

    @pytest.mark.parametrize("path", ["/openapi.json", "/docs", "/redoc"])
    def test_配信するときは_API_文書を公開しない(self, dist_client: TestClient, path: str) -> None:
        resp = dist_client.get(path)

        assert resp.text == INDEX_HTML

    def test_配信しないときは_openapi_を公開する(self) -> None:
        resp = TestClient(create_app(frontend_dist_dir=None)).get("/openapi.json")

        assert resp.status_code == 200
        assert "openapi" in resp.json()

    def test_配信先が無ければ画面を配信しない(self) -> None:
        resp = TestClient(create_app(frontend_dist_dir=None)).get("/exercises/abc")

        assert resp.status_code == 404
