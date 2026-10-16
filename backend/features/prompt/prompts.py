GENERATION_PROMPT_TEMPLATE = """\
次のルールと記録をもとに、筋トレのプログラムを作ってください。依頼は末尾の「依頼」に書きます。
返答は「JSON の形」に沿った JSON だけにしてください。

## プログラム作成ルール

{rules_body}

## 種目一覧と現在のトレーニングマックス

{exercise_lines}

## 直近28日の記録

```csv
{recent_csv}```
{design_note_section}
## JSON の形

```json
{json_example}
```

- target_percent はトレーニングマックスに対する % で、70 は 70% を表す
- トレーニングマックスを使う種目は target_rpe か target_percent のどちらか一方を書く
- ダブルプログレッションの種目は reps に回数の下限、reps_max に上限を書き、target_rpe と target_percent は書かない
- 種目一覧に無い種目は new_exercises に定義する。派生種目は parent と coefficient を、それ以外は e1rm_divisor を書く
- body_part は chest、back、shoulders、arms、legs、abs のどれか
- tm_auto_update は RPE 型のプログラムなら true、% で重量の上げ方を組み込んだプログラムなら false
- start_date は今日以前で、進行中のプログラムの開始日と最後の記録の日付より後にする
- ダブルプログレッションの種目の reps_max は reps 以上にする

## 依頼

"""

DESIGN_NOTE_SECTION_TEMPLATE = """
## 進行中のプログラムの設計メモ

{design_note}
"""

JSON_EXAMPLE = """\
{
  "name": "2026 増量期",
  "start_date": "2026-09-28",
  "tm_auto_update": true,
  "design_note": "ブロックA→デロード→ブロックB",
  "new_exercises": [
    {"name": "ラーセンベンチ", "body_part": "chest", "parent": "ベンチプレス", "coefficient": 0.85,
     "increment_kg": 2.5, "default_rest_seconds": 180},
    {"name": "ケーブルフライ", "body_part": "chest", "e1rm_divisor": 33.3, "increment_kg": 2.5,
     "default_rest_seconds": 90}
  ],
  "weeks": [
    {
      "week": 1, "label": "ブロックA",
      "days": [
        {
          "day": 1, "weekday": "mon",
          "exercises": [
            {"exercise": "スクワット", "sets": 4, "reps": 5, "target_rpe": 7.5},
            {"exercise": "ラットプルダウン", "sets": 2, "reps": 10, "reps_max": 12}
          ]
        }
      ]
    }
  ]
}"""

REVIEW_PROMPT_TEMPLATE = """\
筋トレの記録を見て、この重量のままでよいかを相談させてください。
{from_date}〜{to_date} の記録、プログラム作成ルール、進行中のプログラムの設計メモ、
トレーニングマックスの履歴を渡します。

## 記録

```csv
{csv}```

## プログラム作成ルール

{rules_body}
{design_note_section}
## トレーニングマックスの履歴

{training_max_lines}
"""
