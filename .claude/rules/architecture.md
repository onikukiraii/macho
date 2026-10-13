# アーキテクチャ

どこに何を配置し、依存関係をどちらの向きに流すかを定義する。個別のコードの書き方は
[backend.md](./backend.md) / [frontend.md](./frontend.md) / [database.md](./database.md) を、新規機能やテーブルの作成手順は [new-api.md](../../docs/new-api.md) や [new-model.md](../../docs/new-model.md) を参照。

## 全体構成

```
backend/                     FastAPI + SQLAlchemy + Alembic / Python 3.14 / uv
├── main.py                  アプリのエントリーポイントとルーター登録
├── dependencies.py          コンポジションルート。具象クラスを注入する唯一の場所
├── features/                機能ディレクトリの置き場
│   ├── exercise/            1機能 = 1ディレクトリ
│   ├── program/
│   ├── training_log/
│   └── rest_timer/
├── common/                  機能ディレクトリから参照される共通モジュール
│   ├── db/entities/         全テーブル定義
│   ├── db/session.py        エンジンと SessionLocal
│   ├── gateway/             共通の外部連携。JobQueue
│   ├── errors.py            ドメイン例外
│   └── config.py            環境変数
├── worker/                  Celery アプリと非同期タスク
├── scripts/                 1回きりの実行スクリプト。移行
├── alembic/                 マイグレーション設定と履歴
└── tests/                   機能ディレクトリに対応するテスト

frontend/src/                React 19 + TypeScript + Vite + Tailwind CSS v4
├── main.tsx                 ルートのレンダリングとアプリ全体の Provider
├── App.tsx                  ルーティング定義
├── api/                     API クライアントと型
├── pages/                   ルーターが直接指す画面
├── layouts/                 レイアウト枠を定義し、Outlet で子要素を描画するコンポーネント
├── components/dads/         デジタル庁デザインシステムから取り込んだ部品
├── components/ui/           shadcn/ui の CLI 生成物
├── components/              自前の共通コンポーネント
├── hooks/                   React のライフサイクルや state を扱うカスタムフック
├── lib/                     React に依存しない純粋関数
└── test/                    テストのセットアップと共通ヘルパー
```

## バックエンドは機能ごとに分ける

レイヤーごとの横断ディレクトリ（`routers/`、`services/`、`repositories/` など）は作らず、1つの機能に関するコードを `backend/features/<機能>/` の1ディレクトリに集約する。`features/` 直下には機能ディレクトリ以外を置かない。機能を削除する際には、ディレクトリごと削除できる状態を保つ。

### 機能ディレクトリのファイル構成

| ファイル | 書くもの | 書いてはいけないもの |
|---------|---------|-------------------|
| `router.py` | パス、HTTP ステータス、`Depends`、DTO への変換、ドメイン例外から `HTTPException` への変換 | ビジネスロジック、SQL、計算、具象クラス名 |
| `service.py` | protocol と `_pure` の呼び出し順序、トランザクション境界、`datetime.now(UTC)` や `uuid4()` の生成、`get_today` で受け取った業務日付の利用、ドメイン例外の送出 | 計算式、`Session`、`pywebpush`、プロンプト文言、HTTP の語彙 |
| `_pure.py` | 引数のみから結果を算出する純粋関数 | 引数以外の外部リソースや環境から取得する値（現在時刻や乱数など） |
| `protocol.py` | この機能が外部に要求するインターフェース | 具象実装 |
| `repository.py` | `Session` を受け取るクラス、DB 操作、entity から `types.py` への変換 | `protocol.py` の import、ビジネスロジック、他機能の entity の参照 |
| `gateway.py` | この機能だけで使う外部連携の具象実装、外部ライブラリ例外からドメイン例外への変換 | 複数機能で共有する処理。`common/gateway/` へ配置する |
| `types.py` | ドメインモデルの型定義 | SQLAlchemy の `Mapped`（テーブル定義は `common/db/entities/` に置く） |
| `dto.py` | リクエストとレスポンスの Pydantic モデル | ドメインモデルの型定義 |
| `prompts.py` | プロンプトのテンプレート文字列のみ | `if` などの分岐ロジック（文字列の組み立ては `_pure.py` で行う） |

`gateway.py` と `prompts.py` は必要になったときだけ作成する。中身のない空ファイルは置かない。

ファイル名に `schemas.py` は使用しない。SQLAlchemy 側でも「スキーマ（schema）」という語が使われており、どちらを指しているか判別しにくくなるためである。

### 依存の3つのルール

1. **`_pure.py` が import してよいのは `types.py`、`prompts.py`、`common/errors.py` だけ。**
   外部依存の import が混入すると純粋関数ではなくなってしまうため、import 文を確認するだけでルールの違反を検知できる状態を保つ。

2. **`service.py` は具象実装ファイルを import せず、`protocol.py` のインターフェースだけを参照する。**
   `repository` や `gateway`、`job_queue_celery` などの具象クラスが service に現れた場合、依存の方向が逆転していることを意味する。

   他の機能の `types.py` と `protocol.py` は型注釈のために import してよい。呼び出しは service を経由する。

   業務日付は `get_today` で受け取る。タイムスタンプは service で `datetime.now(UTC)` を生成する。業務日付は `APP_TIMEZONE` の日付で決まり、UTC のタイムスタンプとは日付が異なる時間帯があるため、両者を分けて扱う。

3. **他の機能の `protocol.py` を直接呼ばず、対象機能の `service.py` の関数を経由する。**
   機能 A が機能 B のデータアクセス構造に依存すると、B の変更が A にまで波及してしまう。他機能からの呼び出し窓口は対象機能の `service.py` に一本化する。

抽象インターフェースを定義するのは `protocol.py` のみであり、それ以外はすべて具象実装とする。具象クラス側で `protocol.py` を import や継承する必要はない。Python の Protocol は構造的部分型（ダックタイピング）であるため、メソッドのシグネチャが合致していればインターフェースを満たしていると判定される。

配置に迷ったときは、`_pure.py` の基準に立ち返る。**引数以外の外部リソースや環境から値を取得している処理は、`_pure.py` には置けない。** たとえば現在時刻の取得などは `service.py` で行い、その結果を引数として渡す。

`router.py` でドメイン例外を `HTTPException` に変換するのは、HTTP に関する知識を持ってよい層がルーターのみであるためである。`service.py` で `HTTPException` を送出してしまうと、その service 関数を Celery ワーカーなどの非 HTTP 環境から再利用できなくなる。

## common/

`common/` 配下から各機能ディレクトリを import してはならない。import した時点で共通モジュールとしての責務から逸脱することになる。

- `db/entities/`: 全テーブルの定義を1箇所に集約する。集約する理由と詳細な記述方法は [database.md](./database.md) を参照。
- `gateway/protocol.py`: 複数機能で共有する外部連携インターフェースを定義する。`JobQueue.enqueue` がプリミティブ型しか受け付けないのは、ORM オブジェクトを渡すとプロセス間でのシリアライズ失敗やセッション切断が発生するためである。
- `config.py`: 環境変数を取得・保持するモジュール。ファイルパスの組み立てやキーの命名規則といったロジックは、各機能の `_pure.py` に記述する。

## dependencies.py

どの抽象インターフェースにどの具象実装を割り当てる（依存注入する）かを決定する、プロジェクト内で唯一の場所である。

**戻り値の型注釈は絶対に省略しない。ここが mypy による整合性検証の要となっている。** 具象実装クラスは `protocol.py` を import も継承もしないため、`DbUserRepository` が `UserRepository` Protocol を満たしているかを検証できる場所はここしかない。型注釈を省略すると Protocol が単なるドキュメントと化し、引数や戻り値の不整合を静的解析で検知できなくなる。

Celery ワーカーからも `dependencies.py` の関数を呼び出す。FastAPI の `Depends` 機構は動作しないものの、通常の Python 関数として直接呼び出しが可能である。これにより、具象クラスを組み立てるロジック（DI 設定）をプロジェクト内の1箇所に集約できる。

## 非同期ジョブ

呼び出しの流れは `router` → `service` → `JobQueue.enqueue` の順とする。タスクの実装本体は `worker/tasks.py` に配置し、`dependencies.py` の関数を用いて具象インスタンスを組み立てて実行する。タスクに渡す引数は ID や文字列などのプリミティブ型のみに限定する。

ジョブの状態を DB で管理する場合は、必ず enqueue → commit の順序で行う。先に commit してしまうと、キュー登録に失敗した際に queued 状態のレコードだけが DB に残り、処理待ちなのかエラーで放置されているのか判別できなくなるためである。

## フロントエンドの置き場

- `pages/`: ルーターの `element` が直接指す画面。ファイル名は `<対象>Page.tsx`。
- `layouts/`: レイアウト枠を定義し、`<Outlet />` で子要素を描画するコンポーネント。ファイル名は `<対象>Layout.tsx`。
- `components/dads/`: デジタル庁デザインシステムの React 版コードスニペットから `mise run dads:add` で取り込んだ部品。型エラーの修正以外は手を入れず、ESLint の検証対象からも除外している。
- `components/ui/`: shadcn/ui の CLI が自動生成するコンポーネント。手動で編集せず、ESLint の検証対象からも除外している。
- `components/`: プロジェクト独自の共通コンポーネント。扱う対象を名詞で命名し、曖昧な `Shell` / `Wrapper` / `Container` といった名前は避ける。枠組みを構成するものは `Layout`、1つの値を扱うものは `Field`、状態や通知を伝えるものは `Notice` とする。
- `hooks/`: React のライフサイクルまたは state（状態）に関わるカスタムフックのみを配置する。`use` プレフィックスは「コンポーネントのトップレベルで呼び出す」というフックのルール（Hooks の規約）を示すシグナルであるため、ここに純粋関数を混在させると関数の呼び出し規約が不明瞭になる。
- `lib/`: 純粋関数。React に依存しない。
- `api/`: API クライアントと、`schema.d.ts` から生成・参照した型定義。

依存関係の向きは `pages/` → `hooks/` → `lib/` の一方向とする。`lib/` が hooks を import してしまうと、`lib/` の関数を React 以外の文脈から単独で利用できなくなる。

画面数が増加して `pages/` 直下の見通しが悪くなった段階で、`src/features/<機能>/` ディレクトリを新設し、画面およびその画面専用の hooks や components を集約する。画面が数枚程度の初期段階では過度なディレクトリ分割を行わない。

## アーキテクチャの整合性チェック

```bash
# 具象クラスへの依存が dependencies.py だけに閉じているかを確認する
grep -rn "CeleryJobQueue\|Db[A-Za-z]*Repository\|WebPushSender" \
  --include="*.py" backend/ \
  | grep -v "gateway/job_queue_celery.py\|/repository.py\|/gateway.py\|backend/tests/"
# backend/dependencies.py の行だけが出力されれば正常

mise run lint   # 実装が Protocol を満たしているかは mypy が検証する
```
