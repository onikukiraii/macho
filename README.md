# FastAPI App Template

FastAPI と React で構築するフルスタック Web アプリケーションのテンプレートです。

## 技術スタック (Tech Stack)

- **Backend**: FastAPI, SQLAlchemy, Alembic
- **Frontend**: React 19, TypeScript, Vite 8, Tailwind CSS v4, デジタル庁デザインシステム, shadcn/ui
- **Database**: MySQL 8.0, OpenSearch
- **Storage**: S3 / MinIO
- **LLM**: Claude (Anthropic SDK)
- **Job Queue**: Celery + Redis
- **API 連携**: openapi-typescript + openapi-fetch（型安全な API クライアント）
- **ツール**: uv, mise, Ruff, mypy, ESLint, Vitest

## 前提条件 (Requirements)

- [mise](https://mise.jdx.dev/) (Python, Node.js, uv のバージョン管理およびタスクランナー)
- [Docker](https://www.docker.com/) & Docker Compose

## クイックスタート (Quick Start)

### 1. mise のインストール

```bash
# macOS (Homebrew)
brew install mise
```

### 2. リポジトリのクローン

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

### 3. ツールのセットアップ

```bash
mise install
```

Python 3.14、Node.js 22、uv が自動的にインストールされます。

### 4. 環境変数の設定

```bash
cp .env.template .env
cp frontend/.env.example frontend/.env
```

`.env` を開き、開発環境やプロジェクトの要件に合わせて以下の変数を設定してください:

| 変数 | デフォルト値 | 説明 |
|------|-------------|------|
| `MYSQL_DATABASE` | `mydatabase` | **プロジェクト名への変更を推奨**（例: `myapp`） |
| `MYSQL_USER` | `app` | アプリケーション用のデータベースユーザー名 |
| `MYSQL_PASSWORD` | `password` | アプリケーション用のデータベースパスワード |
| `MYSQL_ROOT_PASSWORD` | `password` | MySQL の root ユーザー用パスワード |

> **注意**: `MYSQL_USER` に `root` は指定できません（MySQL 公式 Docker イメージの仕様上エラーになります）。`root` とは別に作成する一般ユーザーのユーザー名を設定してください。

`DATABASE_URL` についても、上記で設定した `MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE` の内容に合わせて更新してください:

```
DATABASE_URL=mysql+pymysql://<MYSQL_USER>:<MYSQL_PASSWORD>@localhost:3309/<MYSQL_DATABASE>
```

S3、LLM、非同期ジョブ関連の環境変数にはローカル開発用のデフォルト値があらかじめ設定されているため、初期状態のままで動作します。LLM を利用する `review` 機能（契約書レビュー）を試す場合のみ、`ANTHROPIC_API_KEY` を設定してください。

| 変数 | デフォルト値 | 説明 |
|------|-------------|------|
| `S3_BUCKET` | `app-local` | オブジェクトストレージのバケット名 |
| `S3_ENDPOINT_URL` | `http://localhost:9100` | ローカル環境では MinIO を使用。AWS 本番環境では空にして IAM ロール等に委ねます |
| `ANTHROPIC_API_KEY` | （空） | `review` 機能を使用する際に必要 |
| `LLM_MODEL` | `claude-opus-5` | 使用する LLM モデル名 |
| `CELERY_BROKER_URL` | `redis://localhost:6399/0` | 非同期ジョブのブローカー URL |

各環境変数の詳細については [backend/README.md](backend/README.md) を参照してください。プロジェクトで使用しない機能は、開発初期に最小限の手間で安全に削除できます（詳細は同ファイルの「不要な機能の削除」を参照）。

### 5. Docker Compose でコンテナを起動

```bash
docker compose up -d
```

> **ヒント**: `.env` のデータベース設定を変更した後や、DB コンテナが正常に起動しない場合は、Docker ボリュームを削除して再初期化してください:
> ```bash
> docker compose down -v
> docker compose up -d
> ```

コンテナ起動後、以下のサービスへアクセス可能になります:
- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **Worker**: 非同期ジョブワーカー（Celery）
- **MySQL**: localhost:3309
- **OpenSearch**: localhost:9205
- **MinIO**: http://localhost:9100 （管理コンソール: http://localhost:9101）
- **Redis**: localhost:6399

### 6. データベーステーブルの作成

`alembic/versions/` ディレクトリは初期状態では空になっています。テーブル定義自体は `common/db/entities/` に配置されているため、不要な機能を先に削除した上で初期マイグレーションファイルを生成してください。削除手順および対象ファイル一覧については、[backend/README.md](backend/README.md) の「不要な機能の削除」を参照してください。

```bash
mise run migrate-gen "initial"
mise run migrate
```

生成されたマイグレーションファイルの内容を目視で確認し、意図しないテーブル作成や変更が含まれていないことをチェックしてください。

### 7. API 型定義の生成

API サーバーが起動している状態で、以下のコマンドを実行します:

```bash
mise run generate-api
```

## 開発 (Development)

### ローカル開発（Docker を使わずに実行）

```bash
# フロントエンドの依存関係をインストール（初回のみ）
npm install --prefix frontend

# バックエンド開発サーバー起動
mise run dev

# フロントエンド開発サーバー起動（別ターミナルで実行）
mise run dev:front
```

※ MySQL や Redis などのミドルウェアコンテナは事前に起動しておく必要があります（`docker compose up -d db redis` など）。

### コマンド一覧

```bash
mise tasks  # 利用可能なタスク一覧を表示
```

#### バックエンド

| コマンド | 説明 |
|---------|------|
| `mise run dev` | バックエンド開発サーバーを起動 |
| `mise run migrate` | マイグレーションを実行 |
| `mise run migrate-gen "add users table"` | マイグレーションファイルを生成 |
| `mise run worker` | 非同期ワーカーを起動 (Celery) |
| `mise run test` | テストを実行 (pytest) |
| `mise run lint` | Lint チェックを実行 (Ruff + mypy) |
| `mise run format` | コードを自動整形 |

#### フロントエンド

| コマンド | 説明 |
|---------|------|
| `mise run dev:front` | フロントエンド開発サーバーを起動 |
| `mise run lint:front` | Lint チェックを実行 (ESLint + tsc) |
| `mise run format:front` | ESLint によるコード自動修正 |
| `mise run build:front` | 本番用ビルドを実行 |
| `mise run test:front` | テストを実行 (Vitest) |
| `mise run generate-api` | OpenAPI 定義から TypeScript の型を生成 |

#### 横断コマンド

| コマンド | 説明 |
|---------|------|
| `mise run lint:all` | バックエンドとフロントエンドの両方で Lint チェックを実行 |

### 設計規約

規約は `.claude/rules/` にあります。各ファイルの冒頭で `paths` に適用対象を宣言しているため、Claude Code はマッチするファイルを読み込んだときにだけ、その規約をコンテキストに含めます。例えば、フロントエンドの作業中にはバックエンドやデータベースの規約がコンテキストに含まれません。`paths` が効くのは `.claude/rules/*.md` だけで、`CLAUDE.md` とそこから `@` で読み込むファイルは毎セッション全文が展開されます。

| ドキュメント | 内容 | 読み込み条件 |
|-------------|------|------------|
| [.claude/rules/architecture.md](.claude/rules/architecture.md) | アーキテクチャ全体像、ディレクトリ配置、依存関係の方向性 | 常時 |
| [.claude/rules/backend.md](.claude/rules/backend.md) | Python と FastAPI の実装規約・コーディング規約 | `backend/**/*.py` |
| [.claude/rules/database.md](.claude/rules/database.md) | テーブル定義、クエリ作成方針、トランザクション、マイグレーション | `common/db/`、`alembic/`、`repository.py` |
| [.claude/rules/backend-test.md](.claude/rules/backend-test.md) | pytest によるテスト方針とケース設計 | `backend/tests/**/*.py` |
| [.claude/rules/frontend.md](.claude/rules/frontend.md) | React と Tailwind CSS の実装規約・コーディング規約 | `frontend/src/**` |
| [.claude/rules/frontend-test.md](.claude/rules/frontend-test.md) | Vitest と Testing Library によるテスト方針と要素取得 | `__tests__/`、`src/test/` |

新規機能やテーブルの作成手順は `docs/` にあります。こちらは規約ではなく、最初から最後まで通して読むための手順書です。

| ドキュメント | 内容 |
|-------------|------|
| [docs/new-api.md](docs/new-api.md) | 新規機能（エンドポイント）を追加する手順 |
| [docs/new-model.md](docs/new-model.md) | 新規テーブル（entity）を追加する手順 |

### ディレクトリ構成

バックエンドは機能（ドメイン）単位でディレクトリを分割しています。1つの機能に関するコードを `backend/features/<機能>/` に集約し、抽象インターフェースは各機能の `protocol.py` のみで定義します。配置と依存の向きの詳細は [.claude/rules/architecture.md](.claude/rules/architecture.md) を参照してください。

```
.
├── backend/
│   ├── main.py         # アプリケーションのエントリーポイント
│   ├── dependencies.py # コンポジションルート（具象クラスを注入する唯一の場所）
│   ├── features/       # 機能ディレクトリの置き場（1機能 = 1ディレクトリ）
│   │   ├── user/       # 機能実装の最小サンプル
│   │   ├── invoice/    # DB・S3・非同期ジョブを利用するサンプル
│   │   └── review/     # LLM を利用するサンプル
│   ├── common/         # 共通処理（entities / gateway / errors / config）
│   ├── worker/         # Celery アプリケーションと非同期タスク
│   ├── alembic/        # データベースマイグレーション
│   ├── docker/         # Dockerfile
│   └── tests/          # 機能ディレクトリに対応するテストコード
├── frontend/
│   ├── docker/         # Dockerfile
│   ├── src/
│   │   ├── api/        # OpenAPI クライアント・型定義
│   │   ├── components/ # UI コンポーネント (shadcn/ui)
│   │   ├── hooks/      # カスタムフック
│   │   ├── layouts/    # レイアウトコンポーネント
│   │   ├── lib/        # ユーティリティ関数
│   │   ├── pages/      # ページコンポーネント
│   │   └── test/       # テスト共通設定
│   └── package.json
├── .claude/rules/      # 設計規約。paths で適用対象を宣言
├── docs/               # 新規機能やテーブルの作成手順
├── compose.yaml
├── mise.toml           # ツールおよびタスク定義
└── .env.template
```

バックエンドの API 一覧・環境変数・不要な機能の削除手順は [backend/README.md](backend/README.md) にあります。

### なぜ機能ごとに各レイヤーのファイルを持つのか

`routers/`、`services/`、`repositories/` のようにレイヤーで横割りにすると、1つの機能を変更するだけで複数のディレクトリを行き来することになり、無関係な機能のファイルまで視界に入ります。`features/<機能>/` に `types.py` から `router.py` までが並んでいれば、型定義からビジネスロジックまでを1つのディレクトリを開くだけで読めます。コードを探索する AI では、その差がそのままトークン数に出ます。

## ライセンス (License)

MIT
