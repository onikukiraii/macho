from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from features.exercise.types import (
    BodyPart,
    Exercise,
    ExerciseKind,
    ResolvedExercise,
    TrainingMax,
    TrainingMaxRecord,
    TrainingMaxSource,
)
from features.prompt._pure import build_generation_prompt, build_review_prompt
from features.prompt.types import GenerationPromptSource, ReviewPromptSource

TOKYO = ZoneInfo("Asia/Tokyo")
BENCH = Exercise(
    id=1,
    uid="bench",
    name="ベンチプレス",
    body_part=BodyPart.chest,
    parent_id=None,
    coefficient=None,
    e1rm_divisor=40.0,
    increment_kg=2.5,
    default_rest_seconds=180,
)
PAUSE_BENCH = Exercise(
    id=2,
    uid="pause",
    name="ポーズベンチ",
    body_part=BodyPart.chest,
    parent_id=1,
    coefficient=0.9,
    e1rm_divisor=None,
    increment_kg=2.5,
    default_rest_seconds=180,
)
RESOLVED = (
    ResolvedExercise(
        exercise=BENCH, kind=ExerciseKind.training_max, parent=None, e1rm_divisor=40.0, current_training_max=90.5
    ),
    ResolvedExercise(
        exercise=PAUSE_BENCH, kind=ExerciseKind.derived, parent=BENCH, e1rm_divisor=40.0, current_training_max=None
    ),
)
RULES = "## 目標\nBIG3 合計 400kg"
CSV = (
    "日付,Day,種目,重量,回数,RIR,e1RM,予定のレップ,目標RPE,目標重量\n"
    "2026-10-13,第2週 Day2,ベンチプレス,75,5,2,88.1,5,7.5,75\n"
)
DESIGN_NOTE = "ブロックA で RPE7.5 の5回を積む"


def _generation_source(*, design_note: str | None) -> GenerationPromptSource:
    return GenerationPromptSource(rules_body=RULES, exercises=RESOLVED, recent_csv=CSV, design_note=design_note)


class TestBuildGenerationPrompt:
    def test_ルール_種目とトレーニングマックス_直近の記録_設計メモ_JSON_の形の順に入る(self) -> None:
        text = build_generation_prompt(_generation_source(design_note=DESIGN_NOTE))

        markers = [
            RULES,
            "- ベンチプレス: 胸、トレーニングマックス 90.5 kg、分母 40、上げる幅 2.5 kg、レスト 180 秒",
            "- ポーズベンチ: 胸、ベンチプレスの派生種目 × 0.9、上げる幅 2.5 kg、レスト 180 秒",
            CSV,
            DESIGN_NOTE,
            '"weeks": [',
        ]
        positions = [text.find(marker) for marker in markers]
        assert -1 not in positions
        assert positions == sorted(positions)

    def test_進行中のプログラムが無ければ設計メモの節を入れない(self) -> None:
        text = build_generation_prompt(_generation_source(design_note=None))

        assert "設計メモ" not in text


class TestBuildReviewPrompt:
    def test_期間の記録_ルール_設計メモ_トレーニングマックスの履歴の順に入る(self) -> None:
        source = ReviewPromptSource(
            from_date=date(2026, 9, 14),
            to_date=date(2026, 10, 14),
            csv=CSV,
            rules_body=RULES,
            design_note=DESIGN_NOTE,
            training_max_records=(
                TrainingMaxRecord(
                    exercise_name="ベンチプレス",
                    training_max=TrainingMax(
                        exercise_id=1,
                        value=90.5,
                        effective_at=datetime(2026, 10, 11, 15, 0, tzinfo=UTC),
                        source=TrainingMaxSource.auto,
                        reason="第2週の評価",
                    ),
                ),
            ),
        )

        text = build_review_prompt(source, timezone=TOKYO)

        markers = ["2026/09/14〜2026/10/14", CSV, RULES, DESIGN_NOTE, "- 2026/10/12 ベンチプレス 90.5 kg: 第2週の評価"]
        positions = [text.find(marker) for marker in markers]
        assert -1 not in positions
        assert positions == sorted(positions)
