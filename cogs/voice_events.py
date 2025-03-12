import discord
import datetime
import pytz
from discord.ext import commands
from utils.helpers import normalize_text_channel_name
from utils.channel_manager import ChannelManager
from config import CATEGORY_NAME, EXCLUDED_CATEGORY_IDS, debug_log

jst = pytz.timezone("Asia/Tokyo")

class VoiceEventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_manager = ChannelManager(bot)

    def is_excluded(self, channel):
        """チャンネルが指定されたカテゴリー ID のいずれかに属しているか確認"""
        return channel and channel.category and channel.category.id in EXCLUDED_CATEGORY_IDS

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """ボイスチャンネルの入室・退出ログをテキストチャンネルに記録（ミュート・カメラ変更は無視）"""
        guild = member.guild
        now = datetime.datetime.now(jst).strftime("%Y%m%d")

        # **退室ログの処理（移動時も記録する）**
        if before.channel and before.channel != after.channel:
            print(f"[{datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")}][VOICE LEAVE] {member.display_name} が `{before.channel.name}` から退出")
            debug_log(f"[VOICE LEAVE] {member.display_name} が `{before.channel.name}` から退出")

            if self.is_excluded(before.channel):
                debug_log(f"[SKIP] `{before.channel.name}` は除外カテゴリー (`{before.channel.category.id}`) に属するため無視")
            else:
                target_channel = await self.channel_manager.get_or_create_text_channel(guild, before.channel)

                embed = discord.Embed(
                    description=f"**{member.display_name}**（ID: `{member.id}`）が **{before.channel.name}** から退出しました。",
                    color=0xE74C3C
                )
                embed.set_author(name=f"{member.display_name} さんの退出", icon_url=member.display_avatar.url)
                embed.set_footer(text=datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S"))

                await target_channel.send(embed=embed)

        # **入室ログの処理**
        if after.channel and before.channel != after.channel:
            print(f"[{datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")}][VOICE JOIN ] {member.display_name} が `{after.channel.name}` に入室")
            debug_log(f"[VOICE JOIN] {member.display_name} が `{after.channel.name}` に入室")

            if self.is_excluded(after.channel):
                debug_log(f"[SKIP] `{after.channel.name}` は除外カテゴリー (`{after.channel.category.id}`) に属するため無視")
            else:
                target_channel = await self.channel_manager.get_or_create_text_channel(guild, after.channel)

                embed = discord.Embed(
                    description=f"**{member.display_name}**（ID: `{member.id}`）が **{after.channel.name}** に入室しました。",
                    color=0x2ECC71
                )
                embed.set_author(name=f"{member.display_name} さんの入室", icon_url=member.display_avatar.url)
                embed.set_footer(text=datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S"))

                await target_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(VoiceEventsCog(bot))
