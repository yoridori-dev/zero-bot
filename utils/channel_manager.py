import discord
import datetime
import pytz
import asyncio
from utils.helpers import normalize_text_channel_name
from config import CATEGORY_NAME, debug_log

jst = pytz.timezone("Asia/Tokyo")

class ChannelManager:
    """ボイスチャンネルとテキストチャンネルの管理を統一"""
    def __init__(self, bot):
        self.bot = bot
        self.voice_text_mapping = {}
        self.max_cache_size = 10
        self.cleanup_interval = 3600
        self.cleanup_task = None

    async def start_cleanup_task(self):
        """Bot の起動時にキャッシュクリアタスクを開始"""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self.cleanup_old_cache())
        debug_log("[TASK] キャッシュクリアタスクを開始")

    async def get_or_create_text_channel(self, guild, voice_channel):
        debug_log(f"[GET_CHANNEL] {voice_channel.name} に対応するテキストチャンネルを取得または作成")

        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)

        if category is None:
            debug_log(f"[CREATE_CATEGORY] {CATEGORY_NAME} カテゴリが存在しないため新規作成")
            category = await guild.create_category(CATEGORY_NAME)

        today_date = datetime.datetime.now(jst).strftime("%Y%m%d")
        expected_channel_name = f"{today_date}_{normalize_text_channel_name(voice_channel.name)}"

        debug_log(f"[EXPECTED_NAME] 期待するテキストチャンネル名: `{expected_channel_name}`")

        # 既存のキャッシュを確認
        if voice_channel.id in self.voice_text_mapping:
            debug_log(f"[CACHE_HIT] `{voice_channel.name}` のテキストチャンネルはキャッシュ済み: `{self.voice_text_mapping[voice_channel.id].name}`")
            return self.voice_text_mapping[voice_channel.id]

        # 既存のテキストチャンネルを検索
        target_channel = discord.utils.get(category.text_channels, name=expected_channel_name)

        if target_channel:
            debug_log(f"[EXISTING_CHANNEL] 既存のテキストチャンネル `{expected_channel_name}` を使用")
            self.voice_text_mapping[voice_channel.id] = target_channel
        else:
            debug_log(f"[NEW_CHANNEL] テキストチャンネル `{expected_channel_name}` を新規作成")
            target_channel = await guild.create_text_channel(expected_channel_name, category=category)
            await target_channel.send(f"このテキストチャンネルは <#{voice_channel.id}> に紐づいています。")
            self.voice_text_mapping[voice_channel.id] = target_channel

            # キャッシュ管理: サイズが超過した場合、最も古いものを削除
            if len(self.voice_text_mapping) > self.max_cache_size:
                removed_channel_id = next(iter(self.voice_text_mapping))
                del self.voice_text_mapping[removed_channel_id]
                debug_log(f"[CACHE_CLEANUP] キャッシュサイズ超過のため `{removed_channel_id}` を削除")

        return target_channel

    async def cleanup_old_cache(self):
        """定期的に古いキャッシュを削除するタスク"""
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval)

                all_voice_channels = {vc.id for guild in self.bot.guilds for vc in guild.voice_channels}
                removed_channels = []

                for vc_id in list(self.voice_text_mapping.keys()):
                    if vc_id not in all_voice_channels:
                        del self.voice_text_mapping[vc_id]
                        removed_channels.append(vc_id)

                if removed_channels:
                    debug_log(f"[CACHE CLEANUP] {len(removed_channels)} 件の古いキャッシュを削除しました")

                if len(self.voice_text_mapping) > self.max_cache_size:
                    excess = len(self.voice_text_mapping) - self.max_cache_size
                    for _ in range(excess):
                        removed_channel_id = next(iter(self.voice_text_mapping))
                        del self.voice_text_mapping[removed_channel_id]

                    debug_log(f"[CACHE CLEANUP] キャッシュサイズが上限 ({self.max_cache_size}) を超えたため、{excess} 件を削除しました")
        except asyncio.CancelledError:
            debug_log("[CLEANUP TASK] Bot の終了を検知、タスクを停止します")

    async def stop_cleanup_task(self):
        """Bot のシャットダウン時にタスクを停止"""
        if self.cleanup_task:
            debug_log("[CLEANUP TASK] タスクをキャンセルします")
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                debug_log("[CLEANUP TASK] タスクが正常にキャンセルされました")
