import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from features.program_import.router import INVALID_JSON_LOCATION, INVALID_JSON_MESSAGE, MISSING_FIELD_MESSAGE

VALID_PROGRAM: dict[str, Any] = {
    "name": "ベンチ スモロフ Jr",
    "start_date": "2026-10-19",
    "tm_auto_update": False,
    "new_exercises": [
        {
            "name": "ケーブルフライ",
            "body_part": "chest",
            "e1rm_divisor": 33.3,
            "increment_kg": 2.5,
            "default_rest_seconds": 90,
        }
    ],
    "weeks": [
        {
            "week": 1,
            "label": "導入",
            "days": [
                {"day": 1, "weekday": "mon", "exercises": [{"exercise": "ケーブルフライ", "sets": 2, "reps": 10}]}
            ],
        }
    ],
}
WITHOUT_NAME = {key: value for key, value in VALID_PROGRAM.items() if key != "name"}
WITHOUT_BODY_PART = {
    **VALID_PROGRAM,
    "new_exercises": [{key: value for key, value in VALID_PROGRAM["new_exercises"][0].items() if key != "body_part"}],
}


class TestCreateProgramPreview:
    @pytest.mark.parametrize(
        ("json_text", "expected"),
        [
            ('{"name": "ベンチ', [{"location": INVALID_JSON_LOCATION, "message": INVALID_JSON_MESSAGE}]),
            (json.dumps(WITHOUT_NAME), [{"location": "name", "message": MISSING_FIELD_MESSAGE}]),
            (
                json.dumps(WITHOUT_BODY_PART),
                [{"location": "new_exercises[0].body_part", "message": MISSING_FIELD_MESSAGE}],
            ),
        ],
    )
    def test_JSON_として読めないか形が違えば場所と理由を返す(
        self, client: TestClient, json_text: str, expected: list[dict[str, str]]
    ) -> None:
        response = client.post("/api/program-imports/preview", json={"json_text": json_text})

        assert (response.status_code, response.json()) == (200, {"status": "invalid", "issues": expected})
