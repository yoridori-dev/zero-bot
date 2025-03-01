import discord
import datetime
import pytz
from discord.ext import commands
from utils.channel_manager import ChannelManager
from config import debug_log  # DEBUGログ用

jst = pytz.timezone("Asia/Tokyo")

class MessageHandlerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_manager = ChannelManager(bot)

    @commands.Cog.listener()
    async def on_message(self, message):
        """ボイスチャンネルのテキストチャットのメッセージのみ転記"""
        now = datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")

        debug_log(f"{now} - on_message: {message.author.display_name} ({message.author.id})")
        debug_log(f"    チャンネル: {message.channel.name} ({message.channel.id})")
        debug_log(f"    メッセージ: {message.content}")

        if message.author.bot:
            debug_log(f"{message.author.display_name} のメッセージはBOTのため無視")
            return

        guild = message.guild
        if guild is None:
            debug_log(f"ギルド情報が取得できないため無視")
            return

        if not isinstance(message.channel, discord.VoiceChannel):
            debug_log(f"{message.channel.name} はボイスチャンネルではないため無視")
            return  

        target_channel = await self.channel_manager.get_or_create_text_channel(guild, message.channel)
        debug_log(f"転記先チャンネル: {target_channel.name} ({target_channel.id})")

        message_time_jst = message.created_at.replace(tzinfo=pytz.utc).astimezone(jst).strftime("%Y/%m/%d %H:%M:%S")

        image_urls = [attachment.url for attachment in message.attachments]

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
