# Backend

FastAPI + SQLAlchemy + Alembic / Python 3.14 / パッケージ管理: uv

機能（ドメイン）単位でディレクトリを分割し、レイヤー（層）ごとの横断的なディレクトリ分割は行いません。1つの機能に関するコードを `features/<機能>/` の1ディレクトリ内に集約して管理します。`features/` 直下には機能ディレクトリのみを配置します。

新規機能の追加手順は [docs/new-api.md](../docs/new-api.md)、テーブルの追加手順は [docs/new-model.md](../docs/new-model.md) を参照してください。また、アーキテクチャ設計規約は [.claude/rules/architecture.md](../.claude/rules/architecture.md)、バックエンド実装規約は [.claude/rules/backend.md](../.claude/rules/backend.md)、データベース設計規約は [.claude/rules/database.md](../.claude/rules/database.md)、テスト方針は [.claude/rules/backend-test.md](../.claude/rules/backend-test.md) を参照してください。

## 提供 API 一覧

すべてのパスは `/api` で始まります。

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/exercises` | 種目の一覧の取得 |
| GET | `/api/exercises/{uid}` | 種目の詳細とトレーニングマックスの履歴の取得 |
| POST | `/api/exercises` | 種目の作成 |
| PUT | `/api/exercises/{uid}` | 種目の更新 |
| POST | `/api/exercises/{uid}/training-maxes` | トレーニングマックスの手動の変更 |
| GET | `/api/training-logs` | 期間を指定したトレーニング記録の一覧の取得 |
| GET | `/api/training-logs/latest` | 直近のトレーニング記録の取得 |
| GET | `/api/training-logs/day-options` | 記録を開始する Day の選択肢の取得 |
| POST | `/api/training-logs` | トレーニング記録の作成。前の週のトレーニングマックスを評価する |
| GET | `/api/training-logs/{uid}` | トレーニング記録の詳細の取得 |
| PATCH | `/api/training-logs/{uid}` | トレーニング記録のメモの更新 |
| DELETE | `/api/training-logs/{uid}` | トレーニング記録の削除 |
| POST | `/api/training-logs/{uid}/exercises` | 実施種目の追加 |
| PUT | `/api/training-logs/exercises/{performed_uid}` | 実施種目の差し替えとメモの更新 |
| PUT | `/api/training-logs/exercises/{performed_uid}/sets` | 実施種目のセットの置き換え |
| GET | `/api/training-logs/by-exercise/{exercise_uid}` | 種目ごとの履歴の取得 |
| GET | `/api/training-logs/program-progress` | 進行中のプログラムの Day ごとの消化状況の取得 |
| GET | `/api/training-logs/export` | 期間を指定した CSV の出力 |
| GET | `/api/training-logs/export-count` | 出力されるセット件数の取得 |
| POST | `/api/rest-timer/push-subscriptions` | Web Push の購読の登録 |
| GET | `/api/rest-timer` | 動いているレストタイマーの取得 |
| POST | `/api/rest-timer` | レストタイマーの開始 |
| POST | `/api/rest-timer/extend` | レストタイマーの延長 |
| DELETE | `/api/rest-timer` | レストタイマーの停止 |

API レスポンスは連番の `id` を返さず、UUID の `uid` を返します。

## 環境変数

`.env.template` をコピーして `.env` を作成します。必須の設定項目は `DATABASE_URL`、`VAPID_PRIVATE_KEY`、`VAPID_SUBJECT` で、その他の項目にはローカル開発用のデフォルト値があらかじめ設定されています。

| 変数 | 用途 |
|------|------|
| `DATABASE_URL` | MySQL 接続情報 |
| `VAPID_PRIVATE_KEY` | Web Push の VAPID 秘密鍵 |
| `VAPID_SUBJECT` | Web Push の VAPID subject。`mailto:` か `https:` の URL |
| `APP_TIMEZONE` | 業務日付を決めるタイムゾーン。既定は `Asia/Tokyo` |
| `FRONTEND_DIST_DIR` | 画面のビルド成果物のディレクトリ。設定すると api が画面も配信し、`/docs` と OpenAPI を無効にする |
| `CELERY_BROKER_URL` | 非同期ジョブのブローカー URL（Redis） |
| `CORS_ORIGINS` | CORS で許可するオリジン（JSON 配列形式で指定） |
