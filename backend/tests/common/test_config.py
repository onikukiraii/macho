from pathlib import Path

import pytest
from pydantic import ValidationError

from common.config import Settings


def _settings(**overrides: str) -> Settings:
    values = {
        "database_url": "sqlite://",
        "vapid_private_key": "key",
        "vapid_subject": "mailto:a@example.com",
    } | overrides
    return Settings(_env_file=None, **values)  # type: ignore[call-arg, arg-type]


class TestSettings:
    @pytest.mark.parametrize(
        "overrides",
        [
            {"vapid_private_key": ""},
            {"vapid_subject": ""},
            {"vapid_subject": "http://example.com"},
            {"vapid_subject": "mailto:"},
            {"vapid_subject": "https://"},
            {"app_timezone": "Mars/Base"},
        ],
    )
    def test_起動できない値は_ValidationError_にする(self, overrides: dict[str, str]) -> None:
        with pytest.raises(ValidationError):
            _settings(**overrides)

    def test_環境変数が空なら未設定として扱う(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FRONTEND_DIST_DIR", "")

        assert _settings().frontend_dist_dir is None

    def test_環境変数の_dist_を_Path_で読む(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FRONTEND_DIST_DIR", "/app/dist")

        assert _settings().frontend_dist_dir == Path("/app/dist")
