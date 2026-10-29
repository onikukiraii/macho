import argparse
import logging
from collections.abc import Sequence

from sqlalchemy import update
from sqlalchemy.orm import Session

from common.db.entities import ExerciseRow
from common.db.session import SessionLocal
from features.exercise import service as exercise_service
from features.exercise.repository import DbExerciseRepository
from features.exercise.types import BodyPart

logger = logging.getLogger(__name__)

DEFAULT_REST_SECONDS = 30
DEFAULT_E1RM_DIVISOR = 33.3
INCREMENT_KG = 2.5
COMMON_EXERCISES = (
    ("ダンベルプレス", BodyPart.chest),
    ("インクラインダンベルプレス", BodyPart.chest),
    ("ダンベルフライ", BodyPart.chest),
    ("チェストプレス", BodyPart.chest),
    ("ケーブルクロスオーバー", BodyPart.chest),
    ("腕立て伏せ", BodyPart.chest),
    ("ベントオーバーロー", BodyPart.back),
    ("ダンベルロー", BodyPart.back),
    ("シュラッグ", BodyPart.back),
    ("バックエクステンション", BodyPart.back),
    ("アーノルドプレス", BodyPart.shoulders),
    ("フロントレイズ", BodyPart.shoulders),
    ("アップライトロー", BodyPart.shoulders),
    ("バーベルカール", BodyPart.arms),
    ("EZバーカール", BodyPart.arms),
    ("ケーブルカール", BodyPart.arms),
    ("インクラインダンベルカール", BodyPart.arms),
    ("トライセプスプッシュダウン", BodyPart.arms),
    ("フレンチプレス", BodyPart.arms),
    ("スカルクラッシャー", BodyPart.arms),
    ("キックバック", BodyPart.arms),
    ("ブルガリアンスクワット", BodyPart.legs),
    ("ランジ", BodyPart.legs),
    ("ヒップスラスト", BodyPart.legs),
    ("ハックスクワット", BodyPart.legs),
    ("アダクション", BodyPart.legs),
    ("アブダクション", BodyPart.legs),
    ("クランチ", BodyPart.abs),
    ("ケーブルクランチ", BodyPart.abs),
    ("レッグレイズ", BodyPart.abs),
    ("アブローラー", BodyPart.abs),
)


def set_all_rest_seconds(session: Session, *, seconds: int) -> None:
    session.execute(update(ExerciseRow).values(default_rest_seconds=seconds))
    session.commit()


def add_common_exercises(session: Session) -> list[str]:
    """一般的な種目のうち、同じ名前の種目がまだ無いものを作成し、作成した種目名を返す"""
    repo = DbExerciseRepository(session)
    existing_names = {exercise.name for exercise in repo.list_all()}
    added = [(name, body_part) for name, body_part in COMMON_EXERCISES if name not in existing_names]
    for name, body_part in added:
        exercise_service.create_exercise(
            repo,
            name=name,
            body_part=body_part,
            parent_uid=None,
            coefficient=None,
            e1rm_divisor=DEFAULT_E1RM_DIVISOR,
            increment_kg=INCREMENT_KG,
            default_rest_seconds=DEFAULT_REST_SECONDS,
        )
    return [name for name, _ in added]


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="種目のレストの一括変更と、一般的な種目の追加を行う")
    parser.add_argument("--rest-seconds", type=int, help="すべての種目のレストをこの秒数にする")
    parser.add_argument("--add-common", action="store_true", help="一般的な種目のうち、まだ無いものを追加する")
    args = parser.parse_args(argv)
    if args.rest_seconds is None and not args.add_common:
        parser.error("--rest-seconds か --add-common を指定してください")
    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as session:
        if args.rest_seconds is not None:
            set_all_rest_seconds(session, seconds=args.rest_seconds)
            logger.info("すべての種目のレストを %d 秒にしました", args.rest_seconds)
        if args.add_common:
            logger.info("追加した種目: %s", add_common_exercises(session))


if __name__ == "__main__":
    main()
