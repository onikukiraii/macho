---
paths:
  - "frontend/src/**/*.{ts,tsx,css}"
---

# フロントエンド

React 19 + TypeScript 5.9 + Vite 8 + Tailwind CSS v4 + デジタル庁デザインシステム + shadcn/ui。

ディレクトリ構成や配置ルールは [architecture.md](./architecture.md)、テスト方針は
[frontend-test.md](./frontend-test.md) を参照。本ドキュメントでは、フロントエンドコードの実装規約を定める。

## API の型と呼び出し

型定義はバックエンドの OpenAPI 仕様から自動生成する。フロントエンド側で独自に再定義してはならない。二重定義はバックエンド API の変更時に乖離の原因となる。

```bash
mise run generate-api   # api サーバーを起動した状態で実行する
```

- `src/api/schema.d.ts`: openapi-typescript による自動生成ファイル。手動で編集しない。
- `src/api/constants.ts`: `schema.d.ts` から参照した型エイリアスや、Enum 値を画面表示用の日本語ラベルに変換するマップの定義場所。
- `src/api/fetcher.ts`: openapi-fetch の API クライアントと、レスポンスから `data` を抽出しエラー時に例外を送出する `unwrap` ヘルパー。

**API を呼び出す関数はすべて `fetcher.ts` に集約する。** コンポーネントから `fetch` や `api.GET` などを直接呼び出してはならない。呼び出し箇所が分散すると、エラーハンドリングやベース URL の設定方針が画面ごとにばらつく原因となる。

```ts
export const usersApi = {
  list: async () => unwrap<UserResponse[]>(await api.GET('/users/')),
  create: async (body: UserCreateParams) => unwrap<UserResponse>(await api.POST('/users/', { body })),
}
```

## コンポーネント

- 関数コンポーネントは named export（名前付きエクスポート）とする（例: `export function DashboardPage()`）。default export はアプリケーションのルートコンポーネントのみに限定する。
- コンポーネント分割の基準は「再利用性」ではなく「単一責務」である。他で再利用しないダイアログや一覧テーブルであっても、責務が独立していれば積極的に別コンポーネントとして切り出す。
- UI やレイアウトが大きく異なる表示分岐は、1つのコンポーネント内に条件分岐を増設するのではなく、別コンポーネントに分離する。重複コードによるコストよりも、複雑な条件分岐が絡み合って片方だけを安全に修正・削除できなくなるコストの方が高いためである。
- 同一の UI パターンが3箇所以上で現れた場合は、props でテキストや値を受け取る共通コンポーネントに共通化する。
- props のみを参照して計算するロジックは、コンポーネント内に書かず `lib/` 配下の純粋関数として切り出し、単体テストを作成する。
- クリック可能な要素は用途に応じて明確に使い分ける。アプリ内遷移には `<Link>`、外部サイトへのリンクには `<a>`、それ以外のユーザー操作（送信や開閉など）には `<button>` を使用する。
- 固定文言と動的文言の出し分けは、JSX 内の条件分岐で記述する。何を表示するかをイベントハンドラや `useEffect` の中で決定してはならない。JSX の構造を読むだけで画面の表示パターンを把握できる状態を保つ。

## UI 部品

UI 部品は、指定がない限り[デジタル庁デザインシステム](https://design.digital.go.jp/dads/)の部品を使う。デジタル庁デザインシステムに無い部品に限り shadcn/ui を使い、shadcn/ui にも無いプリミティブは Radix UI を直接使う。

チェックボックスの状態表示などの標準的な振る舞いは、導入済みの UI 部品に委譲し、自作しない。

### デジタル庁デザインシステムの部品

部品は npm パッケージではなく、[React 版のコードスニペット](https://github.com/digital-go-jp/design-system-example-components-react)の main からコードを取り込んで使う。置き場所は `src/components/dads/<Name>/`。

```bash
mise run dads:add <Name>   # 例: mise run dads:add Button
```

- **記憶から書かない。** props やクラス名は版によって変わる。未取り込みの部品は必ず `dads:add` で main から取得する。
- **使い方は stories を読む。** 取り込み対象から `*.stories.tsx` は除外している。props の組み合わせと実装上の注意は、GitHub の `src/components/<Name>/<Name>.stories.tsx` にある。
- **依存する部品も取り込む。** `../Slot` のように別の部品を相対パスで import している場合は、その部品も `dads:add` する。
- **取り込んだら型エラーを直す。** スニペットは React 18 と Tailwind CSS v3 で書かれている。React 19 では `isValidElement` の `props` が `unknown` になるため、`isValidElement<HTMLAttributes<HTMLElement>>(children)` のように型引数を渡す。
- **取り込み元のコミット SHA をコミットメッセージに書く。** `dads:add` が最後に表示する。最新版との差分を追うときの起点になる。
- `src/components/dads/` は ESLint の検証対象から除外している。取り込み直したときの差分を小さく保つため、型エラーの修正以外の手を入れない。

取り込める部品は次のとおり。Accordion, Blockquote, Breadcrumbs, Button, Calendar, Card, Carousel, Checkbox, ChipLabel, DatePicker, Disclosure, Divider, Dl, Drawer, EmergencyBanner, ErrorText, FileUpload, HamburgerMenuButton, Heading, HorizontalMenu, Image, Input, Label, LanguageSelector, Legend, Link, List, MenuList, MenuListBox, ModalDialog, NotificationBanner, PageNavigation, ProgressIndicator, Radio, RequirementBadge, ResourceList, SearchBox, Select, SeparatedDatePicker, Slot, StatusBadge, StepNavigation, SupportText, Switch, Tab, Table, Textarea, UtilityLink。

### 色・文字・角丸

`@digital-go-jp/tailwind-theme-plugin` が定義するデジタル庁デザインシステムの値を使う。Tailwind 標準の `gray-500` や `text-sm` は使わない。

- 色: `key-*`、`solid-gray-*`、`error-*`、`success-*`、`warning-*` などの系統。例: `text-solid-gray-800`、`bg-key-900`
- 文字: `text-std-16N-170` のような、サイズ・太さ・行間を1つにまとめたクラス。系統は `std`、`dns`、`oln`、`mono`、`dsp`
- 角丸: `rounded-8` のようにピクセル数で指定する

### shadcn/ui

デジタル庁デザインシステムに無い部品は Tooltip、通知の sonner、DropdownMenu、Sidebar、Skeleton で、これらは shadcn/ui を使う。`src/index.css` で shadcn/ui の `--primary` などをデジタル庁デザインシステムの色へ対応づけてあるため、`bg-primary` のような shadcn/ui のクラスのままで見た目が揃う。

デジタル庁デザインシステムに同じ部品がある shadcn/ui の import は、ESLint の `no-restricted-imports` でエラーにしている。既存の画面は置き換えが済むまで `eslint.config.js` で除外しており、置き換えたら除外の一覧から外す。

`src/components/ui/` は shadcn/ui の CLI が自動生成するディレクトリである。手動での直接編集は行わず、ESLint の検証対象からも除外している。新しい部品が必要な場合は、以下の CLI コマンドで追加する。

```bash
cd frontend && npx shadcn add <component-name>
```

## 状態

- 排他的な複数の boolean フラグは、1つのユニオン型（Union Types）にまとめる（例: `'idle' | 'loading' | 'succeeded' | 'failed'`）。これにより、複数フラグの手動同期が不要になり、不正な状態の組み合わせが発生しなくなる。
- 同一の情報を複数の形式で重複して保持しない。たとえば URL のクエリパラメータを信頼できる情報源（Single Source of Truth: SoT）とする場合、同一の値をローカルの `useState` にも保持してはならない。状態を二重管理すると同期処理が必要となり、バグの温床となる。
- 既存の API レスポンスや既存 state から算出できる値に対して、新しい state を追加しない（派生状態は変数計算で済ませる）。
- `useEffect` の依存配列（deps）を空にして不要な再実行をごまかしてはならない。依存配列に値を追加して問題が生じる場合、その処理は副作用ではなくイベントハンドラ内で実行すべき処理である。
- 非同期処理を `useEffect` 内から呼び出す場合は、関数を `useCallback` でラップして依存配列に含める。
- ダイアログを閉じた際は、内部の入力状態を適切にリセットする。リセットを怠ると、次回開いた際に前回の入力内容が残ってしまう。
- 保存処理が完了する前に、画面上の表示を先行して確定状態へ変えないこと。入力に連動してタイトルなどが即座に更新されると、サーバーに保存されていないにもかかわらず保存済みであるかのようにユーザーに誤認させるためである。

## 型

- `any` 型は使用しない。型エラーを無理やり消すための `as` によるダウンキャストも行わない。型が一致しない場合は、型定義または実装そのものを修正する。
- 公開する関数の戻り値には明示的に型注釈を付与する。型推論に任せてしまうと、返す値を変更した際に型定義が暗黙のうちに変化してしまうためである。
- props をオプショナル（`?`）にするかどうかは慎重に判断する。常に値が渡されるものは必須（required）とする。オプショナルにすることは「その値を渡さない呼び出しパターンが存在する」と宣言することを意味する。
- 自由形式ではない定型文字列に単なる `string` 型を適用しない。ユニオン型やテンプレートリテラル型を用いて許容値を厳格に制限する。
- 排他的な状態を `undefined` や `null` の有無で表現せず、判別可能なユニオン型（Discriminated Unions）で表現する。
- 既存の型から一部を取り出した部分集合を定義する際は、コメントによる説明ではなく `Pick`、`Omit`、`ReturnType` などのユーティリティ型を活用する。コメントによる型説明は二重管理となり、実装変更時に陳腐化しやすいためである。

## 命名

- grep（全文検索）での特定しやすさを基準に命名する。単なる `close` ではなく `closeUserDialog` のように具体的に命名する。
- 変数名を安易に省略しない。省略形は検索時に漏れる原因となる。
- `data`、`info`、`check`、`element` といった抽象的で曖昧な名前は避ける。何をどのように処理するのかを「動詞＋目的語」で具体的に記述する。
- ファイル名には一貫した命名規則を適用する。ルーターが直接指定する画面コンポーネントは `<対象>Page.tsx`、レイアウト枠を定義するものは `<対象>Layout.tsx`、それ以外は扱う対象を具体的な名詞で命名する。
- `Shell`、`Wrapper`、`Container` といった抽象的な命名は避ける。そのファイルが画面内でどのような役割を担うのかが名前から判別できないためである。

## スタイリング

- Tailwind CSS のユーティリティクラスは JSX 内に直接記述する。クラスを見るだけで見た目のスタイルが把握できるのが Tailwind の利点であり、TypeScript 側で動的にクラス文字列を組み立てると JSX 側からスタイルの追跡が困難になる。2箇所以上で同一スタイルを再利用する場合でも、安易に文字列変数化せず直接記述するかコンポーネントとして共通化する。
- クラス名の結合には `cn()` ヘルパー関数を使用し、`clsx` や `tailwind-merge` を直接呼び出さない。
- 同一の CSS プロパティに影響する複数のクラスを重ねて適用しない。たとえば、既定の文字色を `className` に記述した上で条件付きクラスを被せるような書き方は、Tailwind のクラスが同一詳細度で順序依存となるため、本番ビルドと開発環境で適用順序が逆転して表示崩れの原因となる。選択／非選択などの排他的な状態に応じて、適用するクラス自体を三項演算子で明確に切り替える。
- 値に応じてクラス名をマッピングする辞書オブジェクトを TypeScript 側に定義しない。値によってクラスが切り替わる場合は、その値を props として受け取るコンポーネントを作成する。
- `h-[48px]` のような任意の値（Arbitrary values）は避け、`h-12` などの定義済みユーティリティスケールを使用する。任意値を多用すると、画面間でデザインの微妙なズレが生じる原因となる。
- 要素間の余白は `margin` ではなく親要素の `gap` で調整する。要素の追加や削除の際にマージンの付け外しが不要になる。
- 共通の文字色は親要素で指定し、子要素へ継承（カスケード）させる。個別のアイコンや `span` ごとに同一の色クラスを重複指定しない。
- ブラウザのデフォルト値と同じ指定は省略し、実際にはスタイルに影響を与えていない不要な属性やクラスは削除する。
- グローバル CSS にスタイルを追加しない。ユーティリティクラスで表現できないスタイルに限り、対象コンポーネントの近傍で管理する。

## エラーと表示

- API 呼び出しの `catch` 処理を省略しない。エラーを握り潰すと、操作が正常に完了したとユーザーに誤認させてしまう。
- 操作失敗の通知には `sonner` の toast を使用する。エラー文言はどの操作が失敗したのかが具体的に伝わるようにする（例: 「保存に失敗しました」のように操作対象を明確にする）。
- バックエンドから返された生のエラーメッセージをそのまま画面に表示しない。`unwrap` で安全な `detail` が取得できない場合は、定型の安全なエラー文言にフォールバックする。
- 成功の toast を表示した後の後続処理が失敗するケースがないか確認する。成功通知の直後にエラー通知が表示されるような不自然な挙動を防ぐためである。
- データ読み込み中にセクション全体を丸ごと非表示にしない。値を表示する領域ごとに `Skeleton` を配置する。レイアウトが突然切り替わると、レスポンス返却時に画面がガタつく（レイアウトシフトが発生する）ためである。
- 理由を明示しないまま送信ボタンを非活性（disabled）にしない。押せない理由が画面上に表示されていないと、システムが故障しているのか入力不備があるのかをユーザーが判断できないためである。
- Enter キーによるフォーム送信は、日本語 IME の変換確定操作と競合しやすい。IME 変換確定の Enter キーで意図せず送信されないか実機環境で必ず確認する。
- 未設定や空データなど表示できない値のプレースホルダーには、意味不明な記号ではなく「未設定」や「-」などの明確な表記を用いる。
- 本番ビルドのコードに `console` のログを残さない。
- データベースの内部連番 `id` を画面上に表示しない。

## 過剰な防御を書かない

- 型チェックによって値が限定されている場合は、実行時に重複して同じチェックを行わない。
- 仕様上発生し得ない事象に対する過剰なフォールバック処理は書かない。`?? ''` のように空文字へフォールバックして本来のエラー症状を別の問題にすり替えるような救済処理も避ける。
- システム内部でのみ生成される安全な値に対して、過剰な正規化やバリデーションを行わない。
- 追加する明確な根拠を簡潔に説明できないコードは書かない。

## コマンド

```bash
mise run dev:front       # 開発サーバー
mise run lint:front      # ESLint + tsc --noEmit
mise run format:front    # ESLint --fix
mise run test:front      # Vitest
mise run build:front     # 本番ビルド
mise run generate-api    # OpenAPI から型を生成
```
