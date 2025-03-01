import discord
import os
import asyncio
import datetime
import pytz
from discord.ext import commands, tasks
from utils.drive_uploader import upload_to_drive
from config import ARCHIVE_CATEGORY_NAME, GOOGLE_DRIVE_FOLDER_ID, TARGET_GUILD_ID

jst = pytz.timezone("Asia/Tokyo")  # 日本時間設定

class ArchiveManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.archive_task.start()  # ✅ Bot起動時にスケジュール実行

    def cog_unload(self):
        self.archive_task.cancel()

    @tasks.loop(time=datetime.time(hour=23, minute=45, tzinfo=jst))
    async def archive_task(self):
        """毎日 23:45 に特定のサーバーのみアーカイブを実行"""
        print(f"[DEBUG] アーカイブ処理を開始（対象サーバー: {TARGET_GUILD_ID}）")

        guild = self.bot.get_guild(TARGET_GUILD_ID)  # ✅ 指定したサーバーを取得
        if guild is None:
            print(f"[ERROR] 指定されたサーバー {TARGET_GUILD_ID} が見つかりません。")
            return

        category = discord.utils.get(guild.categories, name=ARCHIVE_CATEGORY_NAME)
        if category is None:
            print(f"[DEBUG] カテゴリ {ARCHIVE_CATEGORY_NAME} が見つかりません。")
            return  # アーカイブカテゴリがない場合はスキップ

        today = datetime.datetime.now(jst).strftime("%Y%m%d")
        yesterday = (datetime.datetime.now(jst) - datetime.timedelta(days=1)).strftime("%Y%m%d")

        for channel in category.text_channels:
            if not channel.name.startswith(today) and not channel.name.startswith(yesterday):
                await self.archive_channel(channel)

    async def archive_channel(self, channel):
        """チャンネルの内容を取得し、Google Drive にアップロード後、削除"""
        print(f"[DEBUG] {channel.name} をアーカイブ処理")

        messages = await self.fetch_channel_messages(channel)
        if not messages:
            print(f"[DEBUG] {channel.name} に保存するメッセージがありません。")
            return

        md_content = self.format_messages_as_md(messages)
        file_name = f"{channel.name}.md"
        file_path = f"/tmp/{file_name}"  # 一時ファイル

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(md_content)

        # ✅ Google Drive へアップロード
        upload_success = upload_to_drive(file_path, GOOGLE_DRIVE_FOLDER_ID)
        if upload_success:
            print(f"[DEBUG] {file_name} を Google Drive にアップロード完了")
            await channel.delete()
            print(f"[DEBUG] チャンネル {channel.name} を削除しました")
        else:
            print(f"[ERROR] Google Drive へのアップロードに失敗しました: {file_name}")

    async def fetch_channel_messages(self, channel):
        """チャンネルの全メッセージを取得"""
        messages = []
        async for message in channel.history(limit=1000, oldest_first=True):
            messages.append(message)
        return messages

    def format_messages_as_md(self, messages):
        """メッセージを Markdown 形式に変換"""
        md_content = ""
        for msg in messages:
            timestamp = msg.created_at.astimezone(jst).strftime("%Y-%m-%d %H:%M:%S")
            md_content += f"**{msg.author.display_name}** [{timestamp}]:\n{msg.content}\n\n"
        return md_content

async def setup(bot):
    await bot.add_cog(ArchiveManager(bot))
