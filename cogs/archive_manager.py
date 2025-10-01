import discord
from discord import app_commands
from discord.ext import commands
import datetime
import pytz
import re
import os
import asyncio
from config import CATEGORY_NAME, debug_log

jst = pytz.timezone("Asia/Tokyo")

class ArchiveManagerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="manage_comment", description="管理者用コマンド")
    @app_commands.describe(date="（yyyymmdd）")
    async def manage_comment(self, interaction: discord.Interaction, date: str):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("エラー: サーバー情報が取得できません。", ephemeral=True)
            return

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("⛔ このコマンドは管理者のみ実行可能です。", ephemeral=True)
            return

        if not re.match(r"^\d{8}$", date):
            await interaction.response.send_message("❌ 無効な日付フォーマットです。`yyyymmdd` 形式で指定してください。", ephemeral=True)
            return

        try:
            threshold_date = datetime.datetime.strptime(date, "%Y%m%d").replace(tzinfo=jst)
        except ValueError:
            await interaction.response.send_message("❌ 無効な日付です。正しい `yyyymmdd` 形式で指定してください。", ephemeral=True)
            return

        debug_log(f"[DELETE ARCHIVE] `{date}` 以前のアーカイブチャンネルを削除します")

        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        if category is None:
            await interaction.response.send_message(f"⚠ `{CATEGORY_NAME}` カテゴリーが見つかりません。", ephemeral=True)
            return

        channels_to_delete = []
        for channel in category.text_channels:
            match = re.match(r"^(\d{8})_", channel.name)
            if match:
                channel_date_str = match.group(1)
                try:
                    channel_date = datetime.datetime.strptime(channel_date_str, "%Y%m%d").replace(tzinfo=jst)
                    if channel_date <= threshold_date:
                        channels_to_delete.append(channel)
                except ValueError:
                    continue

        if not channels_to_delete:
            await interaction.response.send_message(f"✅ `{date}` 以前の削除対象チャンネルはありませんでした。", ephemeral=True)
            return

        await interaction.response.defer()
        confirm_msg = await interaction.followup.send(
            f"⚠ `{date}` 以前の `{len(channels_to_delete)}` 件のアーカイブチャンネルを削除します。実行してもよろしいですか？",
            view=DeleteConfirmView(self.bot, interaction, channels_to_delete)
        )
        self.bot.confirmation_messages[interaction.id] = confirm_msg

class DeleteConfirmView(discord.ui.View):
    def __init__(self, bot, interaction, channels_to_delete):
        super().__init__(timeout=30)
        self.bot = bot
        self.interaction = interaction
        self.channels_to_delete = channels_to_delete

    async def delete_original_message(self):
        """確認メッセージを削除"""
        confirm_msg = self.bot.confirmation_messages.pop(self.interaction.id, None)
        if confirm_msg:
            try:
                await confirm_msg.delete()
            except discord.NotFound:
                pass

    @discord.ui.button(label="削除", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        if interaction.user != self.interaction.user:
            await interaction.followup.send("❌ 実行者のみが削除を確定できます。", ephemeral=True)
            return

        deleted_count = 0
        for channel in self.channels_to_delete:
            try:
                await channel.delete()
                deleted_count += 1
                debug_log(f"[ARCHIVE DELETED] {channel.name} を削除しました。")
            except discord.Forbidden:
                await self.interaction.followup.send(f"❌ `{channel.name}` の削除権限がありません。")
            except Exception as e:
                debug_log(f"⚠ {channel.name} の削除に失敗: {e}")

        await self.delete_original_message()  # ✅ 確認メッセージを削除
        await interaction.followup.send(f"✅ `{deleted_count}` 件のアーカイブチャンネルを削除しました。")

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        if interaction.user != self.interaction.user:
            await interaction.followup.send("❌ 実行者のみがキャンセルできます。", ephemeral=True)
            return

        await self.delete_original_message()  # ✅ 確認メッセージを削除
        await interaction.followup.send("⛔ 削除をキャンセルしました。", ephemeral=True)

async def setup(bot):
    bot.confirmation_messages = {}  # ✅ メッセージ管理用辞書を追加
    await bot.add_cog(ArchiveManagerCog(bot))
