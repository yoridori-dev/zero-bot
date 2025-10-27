import os
import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CATEGORY_NAME = "インチャテキスト"
ARCHIVE_CATEGORY_NAME = "インチャテキスト"
TARGET_VOICE_CHANNEL_ID = int(os.getenv("TARGET_VOICE_CHANNEL_ID", "0"))
STOP_BUTTON_ONLY_COMMAND_USER = os.getenv("STOP_BUTTON_ONLY_COMMAND_USER", "False").lower() == "true"
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
TARGET_GUILD_ID = int(os.getenv("TARGET_GUILD_ID", "0"))

# 転記対象外とするカテゴリー（ID で指定）
EXCLUDED_CATEGORY_IDS = [
    1190510055376818217,  # 管理者専用
    1348635643118354443,  # LABテスト用
    1153343627100176404,  # 面談室
]

# プロフ転記元
MESSAGE_SOURCE_CHANNEL_IDS = [
    1146511568922755102,  # 女性プロフィール
    1146511242396188802,  # 男性プロフィール
]

# 退出時のメッセージ削除処理をスキップするカテゴリーID一覧
LEAVE_MESSAGE_DELETE_EXCLUDED_CATEGORY_IDS = [
    1239840073927888906,  # イベント用
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.guilds = True

# デバッグログ出力
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

def debug_log(message):
    """DEBUG_MODE が True のときのみログを出力"""
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")


# ======== 大喜利bot 用設定 ========

# 「お代出題チャンネル」に出すコントロールメッセージの設置先
OGIRI_PROMPT_CHANNEL_ID = 123456789012345678  # ←サーバのテキストチャンネルIDに置き換え

# 投稿を許可するテキストチャンネルのホワイトリスト
# 空リスト [] の場合、Botが send_messages できる全テキストチャンネルを候補にします
ALLOWED_DEST_CHANNEL_IDS = [
    # 111111111111111111, 222222222222222222,
]

# 表示文言・見た目
OGIRI_CONTROL_MESSAGE = "🎭 **大喜利・お題投下コントロール**\n下のボタンからモーダル入力 → 宛先選択 → 投下してね！"
OGIRI_POST_TITLE = "【お題】"
OGIRI_FOOTER_PREFIX = "出題者："
