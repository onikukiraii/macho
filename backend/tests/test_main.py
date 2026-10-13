from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import create_app

INDEX_HTML = "<html><body>macho</body></html>"
SECRET = "outside-dist-secret"


@pytest.fixture()
def dist_client(tmp_path: Path) -> TestClient:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(INDEX_HTML)
    (tmp_path / "secret.txt").write_text(SECRET)
    return TestClient(create_app(frontend_dist_dir=dist))


class TestFrontendServing:
    def test_画面の_URL_を直接開くと_index_html_を返す(self, dist_client: TestClient) -> None:
        resp = dist_client.get("/exercises/abc")

        assert resp.status_code == 200
        assert resp.text == INDEX_HTML

    @pytest.mark.parametrize(
        ("path", "status_code", "media_type"),
        [
            ("/api/unknown", 404, "application/json"),
            ("/%2e%2e/secret.txt", 200, "text/html"),
        ],
    )
    def test_api_の未知のパスは_JSON_の_404_で_dist_の外は返さない(
        self, dist_client: TestClient, path: str, status_code: int, media_type: str
    ) -> None:
        resp = dist_client.get(path)

        assert resp.status_code == status_code
        assert resp.headers["content-type"].startswith(media_type)
        assert SECRET not in resp.text

    def test_配信するときは_openapi_を公開しない(self, dist_client: TestClient) -> None:
        resp = dist_client.get("/openapi.json")

        assert resp.text == INDEX_HTML

    def test_配信先が無ければ画面を配信しない(self) -> None:
        resp = TestClient(create_app(frontend_dist_dir=None)).get("/exercises/abc")

        assert resp.status_code == 404
