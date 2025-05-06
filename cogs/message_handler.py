import discord
import datetime
import pytz
import os
import logging
from discord.ext import commands
from utils.channel_manager import ChannelManager
from config import debug_log, EXCLUDED_CATEGORY_IDS

# タイムゾーン設定
jst = pytz.timezone("Asia/Tokyo")

# ログ保存ディレクトリとファイルパス
log_dir = "log"
os.makedirs(log_dir, exist_ok=True)
today_str = datetime.datetime.now(jst).strftime("%Y%m%d")
log_file_path = os.path.join(log_dir, f"message_handler_{today_str}.log")

# ログローテート処理（3日より古いログを削除）
for fname in os.listdir(log_dir):
    if fname.startswith("message_handler_") and fname.endswith(".log"):
        try:
            date_str = fname.replace("message_handler_", "").replace(".log", "")
            file_date = datetime.datetime.strptime(date_str, "%Y%m%d")
            if (datetime.datetime.now(jst) - file_date).days > 2:
                os.remove(os.path.join(log_dir, fname))
        except Exception:
            continue

# ログ設定（ファイル出力）
logger = logging.getLogger("message_handler")
logger.setLevel(logging.INFO)

# 重複防止
if not logger.handlers:
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

class MessageHandlerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_manager = ChannelManager(bot)

    def is_excluded(self, channel):
        """チャンネルが除外カテゴリーに属しているかを確認"""
        return channel and channel.category and channel.category.id in EXCLUDED_CATEGORY_IDS

    @commands.Cog.listener()
    async def on_message(self, message):
        """ボイスチャンネルのテキストチャットのメッセージのみ転記"""
        now = datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"[MESSAGE][{message.channel.name}][{message.author.display_name}] {message.content}")
        image_urls = [attachment.url for attachment in message.attachments]
        if image_urls:
            logger.info(f"[IMAGE][{message.channel.name}][{message.author.display_name}] {image_urls[0]}")

        debug_log(f"{now} - on_message: {message.author.display_name} ({message.author.id})")
        debug_log(f"    チャンネル: {message.channel.name} ({message.channel.id})")
        debug_log(f"    メッセージ: {message.content}")

        if message.author.bot:
            debug_log(f"{message.author.display_name} のメッセージはBOTのため無視")
            return

        guild = message.guild
        if guild is None:
            debug_log("ギルド情報が取得できないため無視")
            return

        if not isinstance(message.channel, discord.VoiceChannel):
            debug_log(f"{message.channel.name} はボイスチャンネルではないため無視")
            return

        if self.is_excluded(message.channel):
            debug_log(f"[SKIP] `{message.channel.name}` は除外カテゴリー (`{message.channel.category.id}`) に属するため無視")
            return

        target_channel = await self.channel_manager.get_or_create_text_channel(guild, message.channel)
        debug_log(f"転記先チャンネル: {target_channel.name} ({target_channel.id})")

        message_time_jst = message.created_at.replace(tzinfo=pytz.utc).astimezone(jst).strftime("%Y/%m/%d %H:%M:%S")

        embed = discord.Embed(
            description=message.content,
            color=0x82cded,
        )
        embed.set_author(
            name=f"{message.author.display_name}   {message_time_jst}",
            icon_url=message.author.display_avatar.url
        )

        if image_urls:
            embed.set_image(url=image_urls[0])

        await target_channel.send(embed=embed)
        debug_log(f"メッセージを転記完了: {message.content}")

        for img_url in image_urls[1:]:
            image_embed = discord.Embed(
                color=0x82cded,
            )
            image_embed.set_author(
                name=f"{message.author.display_name}   {message_time_jst}",
                icon_url=message.author.display_avatar.url
            )
            image_embed.set_image(url=img_url)

            await target_channel.send(embed=image_embed)
            debug_log(f"追加の画像を転記: {img_url}")

        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(MessageHandlerCog(bot))
