# デプロイ

自宅の Mac mini で動かし、Tailscale の tailnet に接続した端末からのみアクセスする。アプリはログインを持たない。

iPhone の PWA で Web Push と Service Worker を動かすには、iPhone が信頼する証明書の HTTPS で配信する必要がある。VPN の中でも HTTP では動かない。この文書は、そのための手順と、普通のデプロイに無い注意点をまとめる。

## Tailscale の設定

管理画面の DNS ページで、MagicDNS と HTTPS Certificates を有効にする。アプリの URL は `https://<マシン名>.<tailnet 名>.ts.net` になる。

**マシン名と tailnet 名は公開される。** 証明書の発行は Certificate Transparency のログに残り、誰でも検索できる。公開されて困る名前を付けない。

## HTTPS の配信

`tailscale serve` が証明書の発行と更新を行い、HTTPS をローカルのポートへ中継する。

```bash
# フロントエンド
tailscale serve --bg 37173
# API
tailscale serve --bg --https=8443 http://localhost:37000
tailscale serve status
```

**ホストのポートは 37000 番台にまとめる。** 同じ Mac mini で別のプログラムも動かしているため、衝突しにくい番号にしている。番号は「37 + 元のポートの下3桁」で、`compose.yaml` のホスト側に書いてある。コンテナの内側のポートは元のまま。

**serve の HTTPS のポートはマシンで共有する。** serve が HTTPS で受けられるのは 443、8443、10000 の3つに限られ、同じマシンの別のプログラムと取り合いになる。設定する前に `tailscale serve status` で使用中のポートを確認し、空いているものを使う。

フロントエンドと API の origin が変わるため、次の2つを合わせる。

- フロントエンドのビルド時に `VITE_API_BASE_URL=https://<マシン名>.<tailnet 名>.ts.net:8443` を渡す。`http://` のままだと、HTTPS のページから呼べず混在コンテンツとしてブロックされる
- バックエンドの `.env` に `CORS_ORIGINS=["https://<マシン名>.<tailnet 名>.ts.net"]` を書く。値は `backend/common/config.py` の `cors_origins` に読み込まれる

Vite の開発サーバーをそのまま配信する場合は、`frontend/vite.config.ts` の `server.allowedHosts` に `.ts.net` を足す。足さないと、localhost 以外の Host のリクエストを Vite が拒否する。

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
