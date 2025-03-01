import discord
import datetime
import pytz
from discord.ext import commands
from utils.helpers import normalize_text_channel_name
from config import CATEGORY_NAME

jst = pytz.timezone("Asia/Tokyo")

class VoiceEventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """ボイスチャンネルの入室・退出ログを専用テキストチャンネルに書き込む"""
        guild = member.guild
        now = datetime.datetime.now(jst).strftime("%Y%m%d")

        # 入室時
        if after.channel and before.channel != after.channel:
            voice_channel_name = after.channel.name
            new_channel_name = f"{now}_{normalize_text_channel_name(voice_channel_name)}"
            print(f"[DEBUG] {member.display_name} が {voice_channel_name} に入室 -> 転記先: {new_channel_name}")

            # 転記先のカテゴリを取得または作成
            category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
            if category is None:
                print(f"[DEBUG] カテゴリ {CATEGORY_NAME} が存在しないため新規作成")
                category = await guild.create_category(CATEGORY_NAME)

            # 転記先のテキストチャンネルを取得または作成
            target_channel = discord.utils.get(category.text_channels, name=new_channel_name)
            if target_channel is None:
                print(f"[DEBUG] 転記先チャンネル {new_channel_name} が存在しないため作成")
                target_channel = await guild.create_text_channel(new_channel_name, category=category)

            # 入室ログの埋め込みメッセージ
            embed = discord.Embed(
                description=f"**{member.display_name}**（ID: `{member.id}`）が **{voice_channel_name}** に入室しました。",
                color=0x2ECC71  # 緑
            )
            embed.set_author(
                name=f"{member.display_name} さんの入室",
                icon_url=member.display_avatar.url
            )
            embed.set_footer(text=datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S"))

            await target_channel.send(embed=embed)

        # 退出時
        elif before.channel and after.channel is None:
            voice_channel_name = before.channel.name
            new_channel_name = f"{now}_{normalize_text_channel_name(voice_channel_name)}"
            print(f"[DEBUG] {member.display_name} が {voice_channel_name} から退出 -> 転記先: {new_channel_name}")

            # 転記先のカテゴリを取得または作成
            category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
            if category is None:
                print(f"[DEBUG] カテゴリ {CATEGORY_NAME} が存在しないため新規作成")
                category = await guild.create_category(CATEGORY_NAME)

            # 転記先のテキストチャンネルを取得または作成
            target_channel = discord.utils.get(category.text_channels, name=new_channel_name)
            if target_channel is None:
                print(f"[DEBUG] 転記先チャンネル {new_channel_name} が存在しないため作成")
                target_channel = await guild.create_text_channel(new_channel_name, category=category)

            # 退出ログの埋め込みメッセージ
            embed = discord.Embed(
                description=f"**{member.display_name}**（ID: `{member.id}`）が **{voice_channel_name}** から退出しました。",
                color=0xE74C3C  # 赤
            )
            embed.set_author(
                name=f"{member.display_name} さんの退出",
                icon_url=member.display_avatar.url
            )
            embed.set_footer(text=datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S"))

            await target_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(VoiceEventsCog(bot))
