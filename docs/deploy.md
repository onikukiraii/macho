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

**選んだポートは origin の一部になる。** URL は `https://<マシン名>.<tailnet 名>.ts.net:<ポート>` になる。443 を選ぶとポートは URL に現れない。ポートを変えると origin が変わり、ホーム画面に追加した PWA と通知の購読が使えなくなる。ホーム画面への追加と通知の許可をやり直す。

**ホストのポートは 37000 番台にまとめる。** 同じ Mac mini で別のプログラムも動かしているため、衝突しにくい番号にしている。番号は「37 + 元のポートの下3桁」で、`compose.yaml` と `compose.prod.yaml` のホスト側に書いてある。コンテナの内側のポートは元のまま。

**`tailscale funnel` を使わない。** funnel はインターネットへ公開する。アプリはログインを持たないため、公開すると誰でも記録を読み書きできる。

**Tailscale の ACL で、Mac mini へ到達できる端末を自分の端末に限る。** ログインが無いため、到達できる端末がそのままアクセス権になる。

## 本番の起動

本番は `compose.prod.yaml` で動かす。プロジェクト名は `macho-prod` で、開発用の `compose.yaml` とボリュームが分かれる。

ホストへ公開するのは api の `127.0.0.1:37000` に限る。db と redis は compose のネットワークの中に閉じる。

api と worker には `.env` を丸ごと渡さず、`DATABASE_URL`、`CELERY_BROKER_URL`、`APP_TIMEZONE`、`VAPID_PRIVATE_KEY`、`VAPID_SUBJECT` だけを渡す。MySQL の root パスワードは db だけが持つ。

**Mac mini で開発用の `compose.yaml` を同時に起動しない。** api のホストのポート 37000 が重なる。

### 1. `.env` を作る

`.env.template` をコピーして `.env` を作り、次を設定する。`.env` はリポジトリへコミットしない。

- `MYSQL_PASSWORD` と `MYSQL_ROOT_PASSWORD`。`openssl rand -hex 32` の出力を使う。`@` `:` `/` `%` を含む値は `DATABASE_URL` を壊す
- `MYSQL_USER` と `MYSQL_DATABASE`
- VAPID のキー。次のコマンドが出力する `VAPID_PRIVATE_KEY` と `VITE_VAPID_PUBLIC_KEY` の行を書く。`VAPID_SUBJECT` は `mailto:` で始まる自分の連絡先にする

```bash
(cd backend && uv run python -c "
import base64
from cryptography.hazmat.primitives import serialization as s
from py_vapid import Vapid
v = Vapid(); v.generate_keys()
b64 = lambda b: base64.urlsafe_b64encode(b).decode().rstrip('=')
print('VAPID_PRIVATE_KEY=' + b64(v.private_key.private_numbers().private_value.to_bytes(32, 'big')))
print('VITE_VAPID_PUBLIC_KEY=' + b64(v.public_key.public_bytes(s.Encoding.X962, s.PublicFormat.UncompressedPoint)))
")
```

**VAPID の公開キーはイメージに埋め込まれる。** 画面のビルド時に埋め込むため、`.env` を変えたら `--build` を付けて起動し直す。

### 2. 初回のデプロイ

DB が空なので、ダンプは要らない。

```bash
docker compose -f compose.prod.yaml up -d --build db redis
docker compose -f compose.prod.yaml run --build --rm api uv run alembic upgrade head
docker compose -f compose.prod.yaml up -d --build
```

マイグレーションは db が healthy になってから実行される。

`down -v` を実行してよいのは、手順 3 の初期データの投入が完了する前に限る。初回のマイグレーションが失敗したときも、この条件に含まれる。ボリュームを消して手順 2 からやり直せる。投入の完了後は記録がある DB なので実行しない。記録が消える。

```bash
docker compose -f compose.prod.yaml down -v
```

### 3. 初期データの投入

初回だけ、`data/` の seed から種目、トレーニングマックス、プログラム、過去のトレーニング記録を投入する。seed の形式は `data/README.md` にある。`data/` はイメージに含めず、このコマンドの間だけコンテナへマウントする。種目か記録が1件でもある DB では、スクリプトが中断する。

```bash
docker compose -f compose.prod.yaml run --rm -v ./data:/data:ro api uv run python -m scripts.import_legacy --seed-dir /data
```

**投入の前に `training_maxes.csv` の値を直近の実績に合わせる。** 記録の画面で BIG3 と派生種目の重量欄に出る目標重量は、この値から計算する。行が無い種目は目標重量が出ない。

**投入は週の Day をすべて終えたあとに行う。** `training_logs.csv` の最後の日付を含む週は評価済みとして記録される。週の途中までの記録で投入すると、その週の残りをアプリで記録しても、トレーニングマックスの週ごとの自動更新に使われない。週の途中で投入したときは、翌週の最初の記録の前に、その週の実績を見てトレーニングマックスを手で更新する。

### 4. 2回目以降のデプロイ

記録が貯まった DB を変更するため、ダンプ、`.env`、現在のコミットの退避を先に置く。すべてリポジトリの外へ置き、同じ時刻付きの名前で揃える。

```bash
mkdir -m 700 -p ~/backup
t=$(date +%Y%m%d-%H%M%S)
(umask 077; docker compose -f compose.prod.yaml exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction "$MYSQL_DATABASE"' > ~/backup/macho-$t.sql) \
  && tail -n 1 ~/backup/macho-$t.sql | grep -q '^-- Dump completed' \
  && (umask 077; cp .env ~/backup/macho-$t.env; git rev-parse HEAD > ~/backup/macho-$t.commit) \
  && echo OK
```

`OK` が表示されなければ、ダンプは不完全なので先へ進まない。

パスワードは `MYSQL_PWD` で渡す。コマンドラインに書くと `ps` に表示される。

そのあと、新しいイメージでマイグレーションを実行し、起動し直す。`--build` を付けないと、前回のイメージでマイグレーションが実行される。

```bash
docker compose -f compose.prod.yaml up -d --build db redis
docker compose -f compose.prod.yaml run --build --rm api uv run alembic upgrade head
docker compose -f compose.prod.yaml up -d --build
```

### 5. ダンプから復元する

マイグレーションが途中で失敗したときや、記録を壊したときは、ダンプから戻す。`down -v` は使わない。

1. api と worker を止める。

   ```bash
   docker compose -f compose.prod.yaml stop api worker
   ```

2. 復元するダンプの最終行を確かめる。`<時刻>` は退避したファイルの名前の `macho-` のあとの部分。`OK` が表示されなければ、そのダンプは不完全なので手順 3 へ進まない。

   ```bash
   tail -n 1 ~/backup/macho-<時刻>.sql | grep -q '^-- Dump completed' && echo OK
   ```

3. DB を作り直す。

   ```bash
   docker compose -f compose.prod.yaml exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -e "DROP DATABASE \`$MYSQL_DATABASE\`; CREATE DATABASE \`$MYSQL_DATABASE\`"'
   ```

4. ダンプを流し込む。

   ```bash
   docker compose -f compose.prod.yaml exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot "$MYSQL_DATABASE"' < ~/backup/macho-<時刻>.sql
   ```

5. ダンプと同じ時刻で保存したコミットへ戻してから、`docker compose -f compose.prod.yaml up -d --build` で起動する。ダンプはマイグレーション前のスキーマで、新しいコードとは合わない。

   ```bash
   git checkout "$(cat ~/backup/macho-<時刻>.commit)"
   ```

## Mac mini

**スリープさせない。** レスト終了の通知は、サーバーが予約時刻に送る。スリープ中は送られず、通知が遅れる。

```bash
sudo pmset -a sleep 0
```

**再起動後に自動で復帰させる。** 停電や macOS のアップデートで再起動しても、通知を受けられる状態へ戻す。

- 停電のあとに電源が入るようにする: `sudo pmset -a autorestart 1`
- ログインしなくても動くよう、システム設定で自動ログインを有効にする。FileVault が有効だと自動ログインできないため、FileVault を無効にするか、再起動のたびに手でログインする
- Docker Desktop の設定で「ログイン時に Docker Desktop を起動」を有効にする。コンテナは `restart: unless-stopped` なので、Docker が起動すれば戻る

**外向きの通信を許す。** Web Push は Mac mini から Apple のプッシュサービスへ送る。iPhone 側は Apple から受け取るため、通知の受信に VPN の接続は要らない。タイマーの停止など、アプリの操作には VPN の接続が要る。

## iPhone

1. iOS 16.4 以降にする。それより前は、ホーム画面の Web アプリで Web Push を受け取れない
2. Tailscale のアプリで VPN に接続する
3. Safari でアプリの URL を開き、共有メニューの「ホーム画面に追加」で追加する
4. ホーム画面のアイコンから開き、通知を許可する。Safari のタブのままでは Web Push を受け取れない

## origin とキーを変えない

ホーム画面に追加した Web アプリと通知の購読は、URL の origin に紐付く。マシン名か tailnet 名を変えると origin が変わり、ホーム画面への追加と通知の許可をやり直すことになる。

Web Push を実装したら、VAPID のキーペアを `.env` に置き、作り直さない。キーを作り直すと、既存の購読がすべて無効になる。
