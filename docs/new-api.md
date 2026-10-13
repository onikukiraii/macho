# 新しい機能を作成する手順

ここでは例として、新しく `product` 機能を作成する場合の手順を解説します。

前提条件: [新しいテーブルを作成する手順](./new-model.md) に沿って、事前に entity が作成されている必要があります。

機能に関するコードは1つのディレクトリに集約します。`backend/features/product/` ディレクトリを作成し、依存関係の独立性が高い（外部への依存が少ない）ファイルから順に、以下の7つのファイルを作成していきます。

```
backend/features/product/
├── types.py        ドメインモデルの型定義
├── protocol.py     この機能が外部に要求するインターフェース（プロトコル）
├── _pure.py        純粋関数（引数のみから結果を算出する関数）
├── repository.py   データベースアクセスの具象実装
├── service.py      ユースケースの処理フロー（オーケストレーション）
├── dto.py          リクエスト／レスポンスのデータ転送オブジェクト
└── router.py       HTTP エンドポイント定義（FastAPI Router）
```

## 1. ドメインの型定義

`features/product/types.py`:

```python
from dataclasses import dataclass
from enum import StrEnum


class ProductStatus(StrEnum):
    draft = "draft"
    published = "published"


@dataclass(frozen=True)
class Product:
    uid: str
    name: str
    price: int
    status: ProductStatus
```

SQLAlchemy の entity（`common/db/entities/product.py`）とは別に定義します。service が entity を直接受け取ってしまうと、service がデータベース層の実装詳細に依存してしまうためです。

排他的な状態を表現するために `None` や特殊な番兵（sentinel）文字列を使わないようにしてください。「どの状態にも該当しない」というケースが存在する場合は、判別共用体（Tagged Union）を用いて型で明示的に表現します。

## 2. インターフェースの定義 (Protocol)

`features/product/protocol.py`:

```python
from typing import Protocol

from features.product.types import Product


class ProductRepository(Protocol):
    def get(self, uid: str) -> Product: ...

    def list_published(self) -> list[Product]: ...

    def create(self, *, uid: str, name: str, price: int) -> Product: ...
```

メソッド名にはドメイン（ビジネスロジック）の語彙を使用してください。たとえば `select_with_where()` のような SQL 由来の名前ではなく、`list_published()` のように業務上の意味で命名します。SQL やストレージの語彙がインターフェースに漏れ出さないように設計することが重要です。

Protocol（インターフェース）を定義する最大のメリットは、テスト用の Fake 実装を型安全に受け渡せる点にあります。具象クラスで型注釈を書いてしまうと、テスト時に Fake オブジェクトを渡した段階で mypy の型チェックエラーが発生してしまいます。

## 3. 計算ロジック (_pure.py)

`features/product/_pure.py`:

```python
from common.errors import BusinessRuleViolation
from features.product.types import ProductStatus

MIN_PRICE = 100


def validate_publishable(status: ProductStatus, price: int) -> None:
    if status is not ProductStatus.draft:
        raise BusinessRuleViolation("下書き以外は公開できません。")
    if price < MIN_PRICE:
        raise BusinessRuleViolation(f"価格は{MIN_PRICE}円以上にしてください。")
```

引数以外の外部リソースや環境（現在時刻や乱数、DB、外部 API など）から値を取得してはいけません。外部から値を取得している場合、それは純粋関数ではなくなります。現在時刻（`datetime.now()`）やランダムな UUID（`uuid4()`）の生成などは `service.py` 側で行い、計算に必要な値はすべて関数の引数として渡すようにします。

この層の単体テストを手厚く作成します。データベースやモックが不要なため、テストは高速（数ミリ秒）で安定して動作します。

## 4. データベースの具象実装 (repository.py)

`features/product/repository.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from common.db.entities import ProductRow
from common.errors import NotFound
from features.product.types import Product, ProductStatus


class DbProductRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, uid: str) -> Product:
        row = self._session.execute(select(ProductRow).where(ProductRow.uid == uid)).scalar_one_or_none()
        if row is None:
            raise NotFound(f"product が見つかりません: uid={uid}")
        return _to_domain(row)


def _to_domain(row: ProductRow) -> Product:
    return Product(uid=row.uid, name=row.name, price=row.price, status=ProductStatus(row.status))
```

このファイルで `product.protocol` を import したり継承したりする必要はありません。Python の Protocol は構造的部分型（静的なダックタイピング）であるため、メソッドのシグネチャが合致していれば自動的に Protocol を満たしていると判定されます。

このファイルで特に重要な役割を持つのが、entity からドメイン型への変換を行う `_to_domain()` です。データベーステーブルに新しいカラムが追加された場合でも、変換処理がここにカプセル化されているため、`service.py` 側のコードに影響を与えずに済みます。

一覧取得のクエリには必ず `order_by` を指定してください。MySQL などの RDBMS では明示的なソート指定がない場合に戻り順序が保証されないため、ページネーション時にデータの重複や欠落が発生する原因となります。

## 5. ユースケース処理手順 (service.py)

`features/product/service.py`:

```python
from uuid import uuid4

from features.product._pure import validate_publishable
from features.product.protocol import ProductRepository
from features.product.types import Product


def create_product(repo: ProductRepository, *, name: str, price: int) -> Product:
    return repo.create(uid=str(uuid4()), name=name, price=price)


def publish_product(repo: ProductRepository, *, uid: str) -> Product:
    product = repo.get(uid)
    validate_publishable(product.status, product.price)
    return repo.save_published(product)
```

service では「データを取得する → 計算・検証する → データを保存する」といったビジネスフローの手順（オーケストレーション）のみを記述します。なお、`HTTPException` などの HTTP に依存した例外はここでは送出しないでください。HTTP に依存させてしまうと、バックグラウンドワーカー（Celery）など非 HTTP 環境からこの service 関数を再利用できなくなってしまいます。

## 6. リクエストとレスポンス (dto.py)

`features/product/dto.py`:

```python
from pydantic import BaseModel, Field

from features.product.types import ProductStatus


class ProductCreateParams(BaseModel):
    name: str = Field(min_length=1)
    price: int = Field(ge=0)


class ProductResponse(BaseModel):
    uid: str
    name: str
    price: int
    status: ProductStatus
```

`dto.py` を `types.py`（ドメイン型）と明確に分離する理由は、API の入出力スキーマは外部クライアントとの契約であり、ドメインモデルとは変更頻度や理由が異なるためです。内部のドメインモデルにフィールドを追加しただけで、意図せず API レスポンスの形式が変わってしまうといった事故を防ぐ目的があります。

リクエスト値のフォーマットや範囲チェック（文字数や最小値など）は、Pydantic のバリデーション（`Field` など）で行います。ここでチェックした内容と同一のバリデーションを `_pure.py` で重複して実装しないようにします。

ファイル名に `schemas.py` は使用しません。SQLAlchemy やデータベースの世界でも「スキーマ（schema）」という用語が使われており、どちらを指しているのか混同するのを防ぐためです。

## 7. HTTP ルーター (router.py)

`features/product/router.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from common.errors import BusinessRuleViolation, NotFound
from dependencies import get_product_repository
from features.product import service
from features.product.dto import ProductCreateParams, ProductResponse
from features.product.protocol import ProductRepository
from features.product.types import Product

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/")
def create_product(
    params: ProductCreateParams,
    repo: Annotated[ProductRepository, Depends(get_product_repository)],
) -> ProductResponse:
    product = service.create_product(repo, name=params.name, price=params.price)
    return _to_response(product)


@router.post("/{uid}/publish")
def publish_product(
    uid: str,
    repo: Annotated[ProductRepository, Depends(get_product_repository)],
) -> ProductResponse:
    try:
        product = service.publish_product(repo, uid=uid)
    except NotFound as e:
        raise HTTPException(404, str(e)) from e
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    return _to_response(product)


def _to_response(product: Product) -> ProductResponse:
    return ProductResponse(uid=product.uid, name=product.name, price=product.price, status=product.status)
```

引数の型注釈には `protocol.py` のインターフェースを指定し、FastAPI の `Depends` には `dependencies.py` で定義した具象実装を返す関数を指定します。

## 8. コンポジションルートへの登録 (dependencies.py)

`dependencies.py`:

```python
from features.product.protocol import ProductRepository
from features.product.repository import DbProductRepository


def get_product_repository(session: SessionDep) -> ProductRepository:
    return DbProductRepository(session)
```

関数の戻り値の型注釈（`-> ProductRepository`）は絶対に省略しないでください。具象実装クラス（`DbProductRepository`）が Protocol（`ProductRepository`）のシグネチャを正しく満たしているかどうかを mypy が検証する唯一のチェックポイントがここになります。

## 9. main.py へのルーター登録

`main.py` に作成したルーターを登録します:

```python
from features.product.router import router as product_router

app.include_router(product_router)
```

## 10. テストコードの作成

`tests/product/` ディレクトリ配下に、以下の4種類のテストファイルを作成します。

```
tests/product/
├── test_pure.py        純粋関数のテスト。最も手厚くテストを作成する（DB もモックも不要）
├── test_service.py     ユースケースのテスト。Fake 実装を渡して検証（DB 不要）
├── test_repository.py  リポジトリ実装のテスト。SQLite 実 DB で SQL の正しさを検証
└── test_router.py      API エンドポイントのテスト。dependency_overrides で差し替え
```

必要に応じて `tests/fakes.py` に `InMemoryProductRepository` などの Fake 実装を追加してください。

## 動作確認

以下のコマンドでテストと型チェックを実行します:

```bash
uv run pytest -v
uv run mypy .
```

サーバーを起動した後の確認手順:

- Swagger UI: http://localhost:8000/docs
- リクエスト送信テスト: `curl -X POST http://localhost:8000/products/ -H "Content-Type: application/json" -d '{"name":"Test","price":100}'`

---

## よく使われる実装パターン

### 外部サービスを呼び出す場合

複数の機能から共通して使用する場合は `common/gateway/` に配置し、その機能だけで利用する場合は `features/<機能>/gateway.py` に配置します。

service には具象クラスではなく、Protocol のみを渡すようにします。

```python
def publish_product(repo: ProductRepository, storage: Storage, *, uid: str) -> Product:
    product = repo.get(uid)
    storage.put(product_image_key(uid), body, "image/png")
    return repo.save_published(product)
```

外部サービスを呼び出す具象実装クラス内では、外部ライブラリ固有の例外（例: AWS SDK の `ClientError` など）をキャッチし、プロジェクト共通のドメイン例外に変換して再送出してください。例外の変換を怠ると、`service.py` などの上位レイヤーまで外部ライブラリ固有の例外が漏れ出し、上位レイヤーが外部ライブラリに依存してしまう原因になります。

### LLM を利用する場合

関心事に応じて以下の5つに責務を分割し、適切な場所に配置します。

| 責務 | 配置場所 |
|------|--------|
| インターフェース定義 (Protocol) | `common/gateway/protocol.py` |
| クライアント・モデルID・リトライ制御 | `common/gateway/llm_claude.py` |
| プロンプトのテンプレート文言 | `features/<機能>/prompts.py` |
| プロンプト文字列の組み立て | `features/<機能>/_pure.py` |
| 出力データの型定義 | `features/<機能>/types.py` |

実装例として `review` 機能を参照してください。ログ追跡用の `trace_id` には、検索キーとして利用可能な UUID（`uid`）を指定します。内部的な連番 `id` を使用してしまうと、外部クライアントからの問い合わせや障害調査時にログから該当のトレースを特定できなくなるためです。

### 非同期ジョブを利用する場合

呼び出しの流れは `router` → `service` → `JobQueue.enqueue` の順序で行います。非同期タスクの実装本体は `worker/tasks.py` に定義し、`dependencies.py` の関数を呼び出して具象インスタンスを組み立てて実行します。

```python
@celery_app.task(name=service.ISSUE_TASK_NAME)
def issue_invoice_task(invoice_id: int) -> None:
    with SessionLocal() as session:
        service.issue_invoice(get_invoice_repository(session), get_storage(), get_pdf_renderer(), invoice_id=invoice_id)
```

タスクに渡す引数には、ID や文字列などのプリミティブ型のみを使用してください。SQLAlchemy などの ORM オブジェクトを直接渡すと、プロセス間通信時のシリアライズ失敗や、ワーカー側での DB セッション切断によりエラーが発生します。

ジョブの進行状態をデータベースで管理する場合は、必ず「ジョブの enqueue → トランザクションの commit」の順序で処理を行ってください。先に commit してしまうと、キューへの登録に失敗した際にデータベース上に「queued（処理待ち）」状態のレコードだけが孤立して残り、本当に待機中なのか失敗して放置されているのかが判別できなくなります。

### N+1 問題への対策

リレーション（関連テーブル）を持つ entity の一覧を取得する際は、N+1 問題を防ぐために `selectinload` などを指定して関連レコードを一括で先読み（Eager loading）します。

```python
statement = select(InvoiceRow).options(selectinload(InvoiceRow.lines)).order_by(InvoiceRow.id)
```
