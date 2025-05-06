import discord
import random
import datetime
import pytz
from discord.ext import commands
from utils.helpers import normalize_text_channel_name
from utils.channel_manager import ChannelManager
from config import CATEGORY_NAME, EXCLUDED_CATEGORY_IDS, debug_log, MESSAGE_SOURCE_CHANNEL_IDS

jst = pytz.timezone("Asia/Tokyo")

class VoiceEventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_manager = ChannelManager(bot)
        self.join_message_tracking = {}  # {ユーザーID: (テキストチャンネルID, メッセージID)}

    def is_excluded(self, channel):
        """チャンネルが指定されたカテゴリー ID のいずれかに属しているか確認"""
        return channel and channel.category and channel.category.id in EXCLUDED_CATEGORY_IDS

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """ボイスチャンネルの入室・退出ログをテキストチャンネルに記録"""
        guild = member.guild

        # **入室ログ**
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

                # **入室メッセージのIDを保存**
                self.join_message_tracking[member.id] = (target_channel.id, message.id)

            # 指定チャンネルからユーザーのメッセージリンクを取得して転記
            await self.post_user_recent_message_link(member, after.channel)

        # **退室ログ**
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

                # **入室時のメッセージを削除**
                await self.delete_join_message(member)

    async def delete_join_message(self, member):
        """退室時に、入室時に記録したメッセージを削除"""
        if member.id in self.join_message_tracking:
            channel_id, message_id = self.join_message_tracking.pop(member.id)
            channel = self.bot.get_channel(channel_id)

            if channel:
                try:
                    join_message = await channel.fetch_message(message_id)
                    await join_message.delete()
                    debug_log(f"[DELETE MESSAGE] `{member.display_name}` の入室時のメッセージを削除しました")
                except discord.NotFound:
                    debug_log(f"[DELETE FAILED] `{member.display_name}` のメッセージが見つかりませんでした")

    async def find_latest_message_link(self, member):
        """指定ユーザーの最新メッセージリンクを取得"""
        for channel_id in MESSAGE_SOURCE_CHANNEL_IDS:
            message_source_channel = self.bot.get_channel(channel_id)
            if not message_source_channel:
                debug_log(f"[ERROR] 指定のメッセージチャンネル (ID: {channel_id}) が見つかりません")
                continue

            async for message in message_source_channel.history(limit=100):
                if message.author.id == member.id:
                    message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                    debug_log(f"[FOUND MESSAGE] `{member.display_name}` のメッセージを `{message.channel.name}` で発見")
                    return message_link

        debug_log(f"[NO MESSAGE] `{member.display_name}` のメッセージが見つかりませんでした")
        return None

    async def post_user_recent_message_link(self, member, target_channel):
        """指定チャンネルから取得したメッセージリンクを転記"""
        message_link = await self.find_latest_message_link(member)
        if not message_link:
            return

        intro_messages = [
            "はい、ぷろふぃーゆあげゆ",
            "みてみて、このひとこんなひと",
            "重要だからチェックしとけって話！",
            "おい、これ読んどけ",
            "読まないと損するらしい",
        ]
        random_intro = random.choice(intro_messages)
        message_text = f"{random_intro}\n<@{member.id}> → [メッセージリンク]({message_link})"

        await target_channel.send(message_text)
        debug_log(f"[MESSAGE LINK] `{member.display_name}` のメッセージリンクを転記: {message_link}")

async def setup(bot):
    await bot.add_cog(VoiceEventsCog(bot))
