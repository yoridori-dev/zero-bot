import discord
import datetime
import pytz
from discord.ext import commands
from utils.channel_manager import ChannelManager
from config import debug_log  # DEBUGログ用

jst = pytz.timezone("Asia/Tokyo")

class VoiceEventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_manager = ChannelManager(bot)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """ボイスチャンネルの入室・退出ログを専用テキストチャンネルに書き込む"""
        guild = member.guild
        now = datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")

        debug_log(f"{now} - on_voice_state_update: {member.display_name} ({member.id})")
        debug_log(f"    Before: {before.channel.name if before.channel else 'なし'}")
        debug_log(f"    After : {after.channel.name if after.channel else 'なし'}")

        # 入室時
        if after.channel and before.channel != after.channel:
            debug_log(f"{member.display_name} が {after.channel.name} に入室しました")
            target_channel = await self.channel_manager.get_or_create_text_channel(guild, after.channel)

            embed = discord.Embed(
                description=f"**{member.display_name}**（ID: `{member.id}`）が **{after.channel.name}** に入室しました。",
                color=0x2ECC71
            )
            embed.set_author(name=f"{member.display_name} さんの入室", icon_url=member.display_avatar.url)
            embed.set_footer(text=now)

            await target_channel.send(embed=embed)

        # 退出時
        elif before.channel and after.channel is None:
            debug_log(f"{member.display_name} が {before.channel.name} から退出しました")
            target_channel = await self.channel_manager.get_or_create_text_channel(guild, before.channel)

            embed = discord.Embed(
                description=f"**{member.display_name}**（ID: `{member.id}`）が **{before.channel.name}** から退出しました。",
                color=0xE74C3C
            )
            embed.set_author(name=f"{member.display_name} さんの退出", icon_url=member.display_avatar.url)
            embed.set_footer(text=now)

            await target_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(VoiceEventsCog(bot))
