# Zero-Bot

Zero-Bot は Discord 上でのボイスチャンネルとテキストチャンネルの管理を支援する多機能 Bot です。

---

## 🚀 機能一覧

### 🔊 **ボイスチャンネル連動機能**
- ボイスチャンネルへの入退室ログを自動記録
- ボイスチャンネルごとに専用のテキストチャンネルを作成

### 📁 **アーカイブ機能**
- 毎日 23:45 に古いアーカイブチャンネルのログを Markdown (`.md`) 形式で保存
- Google Drive にアップロードし、対象のチャンネルを削除

### 🎙️ **おやんもコマンド**
- `/おやんも [ユーザー] [(countdown)True / False]` ※countdownはデフォルト「False」
- コマンドで指定ユーザーを寝落ち部屋へ移動
- countdown=Trueでカウントダウン(10秒)後に移動する
- 完了メッセージをランダムで送信する機能をもつ
- STOP ボタンで移動をキャンセル可能

### ☁ **Google Drive 連携**
- `credentials.json` による認証を使用し、Google Drive にアーカイブログを保存

---

## 🛠️ **セットアップ方法**

### 1️⃣ **必要な環境を準備**
- Python 3.8 以上
- Discord API トークン
- Google Drive API 設定 (`client_secrets.json`)

### 2️⃣ **必要なライブラリをインストール**
```sh
pip install -r requirements.txt
