# 新しいテーブルを作成する手順

ここでは例として、新しく `products` テーブルを作成する場合の手順を解説します。

テーブル定義は各機能ディレクトリに分散させず、すべて `common/db/entities/` ディレクトリに集約して管理します。Alembic の `target_metadata` は単一のメタデータを通じて全テーブルを検知しているためです。テーブル定義を分散させてしまうと、`__init__.py` へのインポート漏れが発生した際に「テーブルが削除された」と誤認され、マイグレーション自動生成時に `op.drop_table()` が予期せず生成されてしまうリスクがあります。

## 1. entity の作成

`common/db/entities/product.py`:

```python
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from common.db.entities.base import Base


class ProductRow(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
```

クラス名には末尾に `Row` を付けた `XxxRow` という命名規則を採用します。これにより、ドメイン型（`features/<機能>/types.py` で定義する `Xxx`）とクラス名で明確に区別できるようにします。

外部公開用の `uid` カラムは、内部的な主キーである `id` の直後に定義します。API レスポンスやフロントエンドにはこの `uid` を返却し、内部の連番 `id` は外部に公開しないようにします。

`status` などの状態カラムは entity 側では単純な `str` 型として保持し、`StrEnum` への型変換は `repository.py` の `_to_domain()` 関数で行います。バリデーションの上限値など、アプリケーションロジックに依存するポリシー定数は entity に配置しません。テーブル定義が担うのは物理スキーマの表現のみであり、業務ポリシーは `_pure.py` で管理します。

最大長が見積もれる文字列カラムには `Text` を使用せず、長さを明示した `String(長さ)` を指定してください。上限を見積もれない長文テキストのみ `Text` を使用します。

## 2. `common/db/entities/__init__.py` への追加

```python
from common.db.entities.base import Base
from common.db.entities.product import ProductRow  # 追加
from common.db.entities.user import UserRow

__all__ = ["Base", "ProductRow", "UserRow"]  # 追加
```

**注意: この import の追記を忘れると、次回のマイグレーション自動生成時に Alembic がテーブル削除と判断し、`op.drop_table("products")` が予期せず生成されてしまいます。**

## 3. マイグレーションファイルの生成

```bash
docker compose up -d db
cd backend && uv run alembic revision --autogenerate -m "add products table"
```

生成されたマイグレーションファイルの内容は必ず目視で確認してください。意図しない `drop_table` や `alter_column` などの操作が含まれていないかを検証します。

```bash
uv run ruff check --fix alembic/versions/ && uv run ruff format alembic/versions/
```

## 4. マイグレーションの実行

```bash
mise run migrate
```

## 動作確認

以下のコマンドを実行して、テーブルが正常に作成されているか確認します:

```bash
docker compose exec db sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "SHOW TABLES;"'
```

---

## よく使われる実装パターン

### relationship と cascade（親子関係を持つテーブル）

親子関係を持つテーブルの設計例です。既存コードの `invoices` と `invoice_lines` も実装サンプルとして参考になります。

```python
class OrderRow(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)

    items: Mapped[list["OrderItemRow"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItemRow.id",
    )


class OrderItemRow(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    order: Mapped[OrderRow] = relationship(back_populates="items")
```

- `cascade="all, delete-orphan"` を指定することで、親レコードが削除された際に関連する子レコードも連動して自動削除されます。
- `order_by` を指定して子レコードの取得順序を固定します。指定しない場合、クエリごとに順序が変わる可能性があります。
- 子レコードを一括で更新・差し替えたい場合は、`row.items = [...]` のように新しいリストを再代入します。リストから外れた古いレコードは `delete-orphan` により自動的に削除されます。

### 複合ユニーク制約

```python
from sqlalchemy import UniqueConstraint


class ProductRow(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("tenant_id", "uid"),)
```

複合インデックス `[A, B]` を作成している場合、先頭カラムである `A` 単独のインデックスを別途作成する必要はありません。B-tree インデックスは最左プレフィックスの一致により、複合インデックス側でカラム `A` 単独の検索条件もカバーできるためです。

### 一意制約違反をドメイン例外に変換する

データベースの一意制約違反（`IntegrityError`）は `repository.py` 内でキャッチし、`rollback()` を実行した上でドメイン例外（`Conflict` など）に変換して再送出します。`router.py` などの上位層に SQLAlchemy 固有の例外を直接漏らさないように設計します。

```python
try:
    self._session.commit()
except IntegrityError as e:
    self._session.rollback()
    raise Conflict(f"uid はすでに登録されています: uid={uid}") from e
```

### 循環インポートの回避

双方向のリレーション定義などによる循環インポートは、`typing.TYPE_CHECKING` ガードと文字列による前方参照（型注釈）を利用して回避します。

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from common.db.entities.order import OrderRow
```
