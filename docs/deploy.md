# デプロイ

自宅の Mac mini で動かし、Tailscale の tailnet に接続した端末からのみアクセスする。アプリはログインを持たない。

iPhone の PWA で Web Push と Service Worker を動かすには、iPhone が信頼する証明書の HTTPS で配信する必要がある。VPN の中でも HTTP では動かない。この文書は、そのための手順と、普通のデプロイに無い注意点をまとめる。

## Tailscale の設定

管理画面の DNS ページで、MagicDNS と HTTPS Certificates を有効にする。アプリの URL は `https://<マシン名>.<tailnet 名>.ts.net` になる。

**マシン名と tailnet 名は公開される。** 証明書の発行は Certificate Transparency のログに残り、誰でも検索できる。公開されて困る名前を付けない。

## HTTPS の配信

api が画面も配信するため、公開する origin は1つで済む。`tailscale serve` が証明書の発行と更新を行い、HTTPS を api のローカルのポートへ中継する。

```bash
tailscale serve status
tailscale serve --bg --https=<空いているポート> 37000
```

**serve の HTTPS のポートはマシンで共有する。** serve が HTTPS で受けられるのは 443、8443、10000 の3つに限られ、同じマシンの別のプログラムと取り合いになる。先に `tailscale serve status` で使用中のポートを確認し、空いているものを選ぶ。

**選んだポートは origin の一部になる。** URL は `https://<マシン名>.<tailnet 名>.ts.net:<ポート>` になり、ポートを変えると origin が変わる。443 を選ぶとポートは URL に現れない。

**ホストのポートは 37000 番台にまとめる。** 同じ Mac mini で別のプログラムも動かしているため、衝突しにくい番号にしている。番号は「37 + 元のポートの下3桁」で、`compose.yaml` と `compose.prod.yaml` のホスト側に書いてある。コンテナの内側のポートは元のまま。

**`tailscale funnel` を使わない。** funnel はインターネットへ公開する。アプリはログインを持たないため、公開すると誰でも記録を読み書きできる。

**Tailscale の ACL で、Mac mini へ到達できる端末を自分の端末に限る。** ログインが無いため、到達できる端末がそのままアクセス権になる。

## 本番の起動

本番は `compose.prod.yaml` で動かす。プロジェクト名は `macho-prod` で、開発用の `compose.yaml` とボリュームが分かれる。公開するのは api の `127.0.0.1:37000` に限り、db と redis は compose のネットワークの中に閉じる。

**Mac mini で開発用の `compose.yaml` を同時に起動しない。** api のホストのポート 37000 が重なる。

### 1. `.env` を作る

`.env.template` をコピーして `.env` を作り、次を設定する。`.env` はリポジトリへコミットしない。

- `MYSQL_PASSWORD` と `MYSQL_ROOT_PASSWORD`。推測されにくい値にする
- `MYSQL_USER` と `MYSQL_DATABASE`
- VAPID の鍵。次のコマンドが出す `VAPID_PRIVATE_KEY` と `VITE_VAPID_PUBLIC_KEY` の行を書く。`VAPID_SUBJECT` は `mailto:` で始まる自分の連絡先にする

```bash
cd backend && uv run python -c "
import base64
from cryptography.hazmat.primitives import serialization as s
from py_vapid import Vapid
v = Vapid(); v.generate_keys()
b64 = lambda b: base64.urlsafe_b64encode(b).decode().rstrip('=')
print('VAPID_PRIVATE_KEY=' + b64(v.private_key.private_numbers().private_value.to_bytes(32, 'big')))
print('VITE_VAPID_PUBLIC_KEY=' + b64(v.public_key.public_bytes(s.Encoding.X962, s.PublicFormat.UncompressedPoint)))
"
```

**VAPID 鍵はビルドに入る。** 公開鍵は画面のビルド時にイメージへ埋め込まれる。`.env` を変えたら `--build` を付けて起動し直す。

### 2. 起動とマイグレーション

```bash
docker compose -f compose.prod.yaml up -d --build db redis
docker compose -f compose.prod.yaml run --rm api uv run alembic upgrade head
docker compose -f compose.prod.yaml up -d --build
```

マイグレーションは db が healthy になってから実行される。

### 3. KINNIK の記録の移行

初回だけ、`data/` の CSV と xlsx を取り込む。`data/` はイメージに含めず、このコマンドの間だけコンテナへマウントする。種目か記録が1件でもある DB では、スクリプトが中断する。

```bash
docker compose -f compose.prod.yaml run --rm -v ./data:/data:ro api uv run python -m scripts.import_legacy
```

引数は `uv run python -m scripts.import_legacy --help` で確認する。

**マイグレーションと移行の前に MySQL をダンプし、`.env` を退避する。** どちらもリポジトリの外へ置く。

```bash
docker compose -f compose.prod.yaml exec db sh -c 'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' > ~/backup/macho-$(date +%Y%m%d).sql
cp .env ~/backup/macho.env
```

**移行が途中で失敗したときは、ボリュームを消して作り直す。** 移行は中途半端に書き込まれた DB では再実行できない。

```bash
docker compose -f compose.prod.yaml down -v
```

そのあと、手順 2 からやり直す。

## Mac mini

**スリープさせない。** レスト終了の通知は、サーバーが予約時刻に送る。スリープ中は送られず、通知が遅れる。

```bash
sudo pmset -a sleep 0
```

**外向きの通信を許す。** Web Push は Mac mini から Apple のプッシュサービスへ送る。iPhone 側は Apple から受け取るため、通知の受信に VPN の接続は要らない。タイマーの停止など、アプリの操作には VPN の接続が要る。

## iPhone

1. iOS 16.4 以降にする。それより前は、ホーム画面の Web アプリで Web Push を受け取れない
2. Tailscale のアプリで VPN に接続する
3. Safari でアプリの URL を開き、共有メニューの「ホーム画面に追加」で追加する
4. ホーム画面のアイコンから開き、通知を許可する。Safari のタブのままでは Web Push を受け取れない

## origin と鍵を変えない

ホーム画面に追加した Web アプリと通知の購読は、URL の origin に紐付く。マシン名か tailnet 名を変えると origin が変わり、ホーム画面への追加と通知の許可をやり直すことになる。

Web Push を実装したら、VAPID の鍵ペアを `.env` に置き、作り直さない。鍵を作り直すと、既存の購読がすべて無効になる。
