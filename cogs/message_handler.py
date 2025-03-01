import discord
import datetime
import pytz
from discord.ext import commands
from utils.helpers import normalize_text_channel_name
from config import CATEGORY_NAME

jst = pytz.timezone("Asia/Tokyo")

class MessageHandlerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        """ボイスチャンネル (`discord.VoiceChannel`) に書かれたメッセージのみ転記"""
        print(f"[DEBUG] メッセージ受信: {message.content} （送信者: {message.author.display_name}）")

        if message.author.bot:
            print("[DEBUG] ボットのメッセージなので無視")
            return  # ボットのメッセージは無視

        guild = message.guild
        if guild is None:
            print("[DEBUG] ギルド情報が取得できません。")
            return

        now = datetime.datetime.now(jst).strftime("%Y%m%d")

        # メッセージがボイスチャンネル (`discord.VoiceChannel`) に書かれたものか判定
        if not isinstance(message.channel, discord.VoiceChannel):
            print(f"[DEBUG] {message.channel.name} はボイスチャンネルではないため無視します。")
            return  # ボイスチャンネル以外のメッセージは無視

        print(f"[DEBUG] {message.channel.name} はボイスチャンネルに書かれたメッセージです。転記処理を開始します。")

        # 転記先のテキストチャンネル名を `"yyyymmdd_転送元ボイスチャンネル名"` の形式で作成
        new_channel_name = f"{now}_{normalize_text_channel_name(message.channel.name)}"
        print(f"[DEBUG] 転記先チャンネル名: {new_channel_name}")

        # 転記先のカテゴリを取得または作成
        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        if category is None:
            print(f"[DEBUG] カテゴリ {CATEGORY_NAME} が存在しません。新規作成します。")
            category = await guild.create_category(CATEGORY_NAME)

        # 転記先のテキストチャンネルを取得または作成
        target_channel = discord.utils.get(category.text_channels, name=new_channel_name)
        if target_channel is None:
            print(f"[DEBUG] 転記先チャンネル {new_channel_name} が存在しないため作成")
            target_channel = await guild.create_text_channel(new_channel_name, category=category)

        # 投稿日時を JST に変換
        message_time_jst = message.created_at.replace(tzinfo=pytz.utc).astimezone(jst).strftime("%Y/%m/%d %H:%M:%S")

        # 画像URLリストを取得
        image_urls = [attachment.url for attachment in message.attachments]

        # 最初の `embed`（本文 + 1枚目の画像）
        embed = discord.Embed(
            description=message.content,
            color=0x82cded,
        )
        embed.set_author(
            name=f"{message.author.display_name}   {message_time_jst}",
            icon_url=message.author.display_avatar.url
        )

        # 1枚目の画像があればセット
        if image_urls:
            embed.set_image(url=image_urls[0])

        print(f"[DEBUG] メッセージ転記: {message.content} (画像数: {len(image_urls)})")

        await target_channel.send(embed=embed)  # 最初の `embed` を送信

        # 2枚目以降の画像がある場合、それぞれ新しい `embed` で送信
        for img_url in image_urls[1:]:
            image_embed = discord.Embed(
                color=0x82cded,
            )
            image_embed.set_author(
                name=f"{message.author.display_name}   {message_time_jst}",
                icon_url=message.author.display_avatar.url
            )
            image_embed.set_image(url=img_url)

            await target_channel.send(embed=image_embed)  # 2枚目以降の `embed` を送信

        print(f"[DEBUG] メッセージ転記完了: {message.content}")
        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(MessageHandlerCog(bot))
