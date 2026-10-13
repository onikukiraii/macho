# fastapi_app - FastAPI プロジェクトテンプレート

## プロジェクト構成

- `backend/` - FastAPI (Python 3.14, SQLAlchemy, Alembic)。機能ごとのコードは `backend/features/<機能>/` に集約します。
- `frontend/` - React 19 + TypeScript + Vite + Tailwind CSS v4
- `.claude/rules/` - 設計規約
- `docs/` - 新規機能やテーブルの作成手順

## 規約（MUST）

実装規約は `.claude/rules/` にあります。`architecture.md` は常に適用され、その他の規約は `paths` で対象を絞っているため、該当ファイルを参照した際に読み込まれます。

新規作成の手順は以下を参照してください。

| 作業 | 読むもの |
|------|---------|
| 新しい機能を作る | `docs/new-api.md` |
| 新しいテーブルを作る | `docs/new-model.md` |

## 開発コマンド

タスクは `mise run <task>` で実行します。一覧と説明は `mise tasks` で引いてください。全サービスの起動は `docker compose up -d`（API:8000, Frontend:5173, MySQL:3309）。

## コミット規約

コミット時は `/commit` スキルを使用してください。
