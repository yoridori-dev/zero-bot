import discord
import datetime
import pytz
from discord.ext import commands
from utils.helpers import normalize_text_channel_name
from utils.channel_manager import ChannelManager
from config import CATEGORY_NAME, debug_log

jst = pytz.timezone("Asia/Tokyo")

class VoiceEventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_manager = ChannelManager(bot)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """ボイスチャンネルの入室・退出ログをテキストチャンネルに記録"""
        guild = member.guild
        now = datetime.datetime.now(jst).strftime("%Y%m%d")

        # **退室ログの処理**
        if before.channel:
            voice_channel_name = before.channel.name
            text_channel_name = f"{now}_{normalize_text_channel_name(voice_channel_name)}"
            debug_log(f"[VOICE LEAVE] {member.display_name} が `{voice_channel_name}` から退出")

            target_channel = await self.channel_manager.get_or_create_text_channel(guild, before.channel)

            embed = discord.Embed(
                description=f"**{member.display_name}**（ID: `{member.id}`）が **{voice_channel_name}** から退出しました。",
                color=0xE74C3C
            )
            embed.set_author(name=f"{member.display_name} さんの退出", icon_url=member.display_avatar.url)
            embed.set_footer(text=datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S"))

            await target_channel.send(embed=embed)

        # **入室ログの処理**
        if after.channel:
            voice_channel_name = after.channel.name
            text_channel_name = f"{now}_{normalize_text_channel_name(voice_channel_name)}"
            debug_log(f"[VOICE JOIN] {member.display_name} が `{voice_channel_name}` に入室")

            target_channel = await self.channel_manager.get_or_create_text_channel(guild, after.channel)

            embed = discord.Embed(
                description=f"**{member.display_name}**（ID: `{member.id}`）が **{voice_channel_name}** に入室しました。",
                color=0x2ECC71
            )
            embed.set_author(name=f"{member.display_name} さんの入室", icon_url=member.display_avatar.url)
            embed.set_footer(text=datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S"))

            await target_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(VoiceEventsCog(bot))
