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