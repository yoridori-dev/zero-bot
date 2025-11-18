import discord
import random
import datetime
import pytz
import asyncio
import logging
import os

from discord.ext import commands
from utils.helpers import normalize_text_channel_name
from utils.channel_manager import ChannelManager
from config import CATEGORY_NAME, EXCLUDED_CATEGORY_IDS, debug_log, MESSAGE_SOURCE_CHANNEL_IDS, LEAVE_MESSAGE_DELETE_EXCLUDED_CATEGORY_IDS
from utils.helpers import load_profile_messages, save_profile_messages

# タイムゾーン設定
jst = pytz.timezone("Asia/Tokyo")

# ログ保存ディレクトリとファイルパス
log_dir = "log"
os.makedirs(log_dir, exist_ok=True)
today_str = datetime.datetime.now(jst).strftime("%Y%m%d")
log_file_path = os.path.join(log_dir, f"message_handler_{today_str}.log")

# ログローテート処理（3日より古いログを削除）
for fname in os.listdir(log_dir):
    if fname.startswith("message_handler_") and fname.endswith(".log"):
        try:
            date_str = fname.replace("message_handler_", "").replace(".log", "")
            file_date = datetime.datetime.strptime(date_str, "%Y%m%d")
            if (datetime.datetime.now(jst) - file_date).days > 2:
                os.remove(os.path.join(log_dir, fname))
        except Exception:
            continue

# ログ設定（ファイル出力）
logger = logging.getLogger("message_handler")
logger.setLevel(logging.INFO)

# 重複防止
if not logger.handlers:
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

class VoiceEventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_manager = ChannelManager(bot)
        self.join_message_tracking = {}  # {ユーザーID: (テキストチャンネルID, メッセージID)}
        self.profile_message_map = load_profile_messages()

    def is_excluded(self, channel):
        """チャンネルが指定されたカテゴリー ID のいずれかに属しているか確認"""
        return channel and channel.category and channel.category.id in EXCLUDED_CATEGORY_IDS

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        guild = member.guild

        # ✅ 退室処理
        if before.channel and before.channel != after.channel:
            logger.info(f"[VOICE LEAVE] {member.display_name} が `{before.channel.name}` から退出")

            if not self.is_excluded(before.channel):
                text_channel = await self.channel_manager.get_or_create_text_channel(guild, before.channel)

                embed = discord.Embed(
                    description=f"**{member.display_name}**（ID: `{member.id}`）が **{before.channel.name}** から退出しました。",
                    color=0xE74C3C
                )
                embed.set_author(name=f"{member.display_name} さんの退出", icon_url=member.display_avatar.url)
                embed.set_footer(text=datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S"))

                await text_channel.send(embed=embed)

                # 現在の人数
                member_count = len(before.channel.members)

                # 0人ならメッセージ削除
                if member_count == 0:
                    category_id = before.channel.category_id

                    if category_id not in LEAVE_MESSAGE_DELETE_EXCLUDED_CATEGORY_IDS:
                        await self.delete_all_messages_from_channel(before.channel)
                    else:
                        debug_log(f"[SKIP DELETE] {before.channel.name} は削除対象外カテゴリ（ID: {category_id}）のため削除スキップ")

                # 🔽 プロフィールEmbed削除
                profile_data = self.profile_message_map.get(str(member.id))
                if profile_data:
                    try:
                        channel = self.bot.get_channel(int(profile_data["channel_id"]))
                        message = await channel.fetch_message(int(profile_data["message_id"]))
                        await message.delete()
                        debug_log(f"[DELETE PROFILE LINK] `{member.display_name}` のプロフィール投稿を削除しました")

                        del self.profile_message_map[str(member.id)]
                        save_profile_messages(self.profile_message_map)

                    except Exception as e:
                        debug_log(f"[DELETE ERROR] `{member.display_name}` のプロフィール投稿削除時にエラー: {e}")

        # ✅ 入室処理
        if after.channel and before.channel != after.channel:
            logger.info(f"[VOICE JOIN] {member.display_name} が `{after.channel.name}` に入室")

            if not self.is_excluded(after.channel):
                text_channel = await self.channel_manager.get_or_create_text_channel(guild, after.channel)

                embed = discord.Embed(
                    description=f"**{member.display_name}**（ID: `{member.id}`）が **{after.channel.name}** に入室しました。",
                    color=0x2ECC71
                )
                embed.set_author(name=f"{member.display_name} さんの入室", icon_url=member.display_avatar.url)
                embed.set_footer(text=datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S"))

                sent_msg = await text_channel.send(embed=embed)
                self.join_message_tracking[member.id] = (text_channel.id, sent_msg.id)

                await self.post_user_recent_message_link(member, after.channel)

                # 前いたチャンネルの人数表示
                member_count = len(before.channel.members)

                # 0人チェック
                if member_count == 0:
                    await self.delete_all_messages_from_channel(before.channel)

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
        """指定チャンネルから取得したメッセージリンクを埋め込み形式で転記"""
        message_link = await self.find_latest_message_link(member)
        if not message_link:
            return

        intro_messages = [
            "みてみて、このひとこんなひと",
            "ほらほら、きたよ！挨拶して！！",
            "自己紹介はコチラ！",
            "どんな人か気になる？クリックして！"
        ]
        random_intro = random.choice(intro_messages)

        # ニックネーム優先、なければ表示名
        display_name = member.nick if member.nick else member.display_name

        # 性別ロールIDを指定（サーバーに合わせて変更）
        MALE_ROLE_ID = 1146540517019111597   # man🚹
        FEMALE_ROLE_ID = 1146541261025718273 # woman🚺

        # メンバーのロールID一覧を取得
        member_role_ids = [role.id for role in member.roles]

        # 色を判定
        if MALE_ROLE_ID in member_role_ids:
            embed_color = 0x206694  # 青（男性）
        elif FEMALE_ROLE_ID in member_role_ids:
            embed_color = 0xff00ff  # 赤（女性）
        else:
            embed_color = 0x2ECC71  # 緑（デフォルト）

        embed = discord.Embed(
            title=random_intro,
            description=f"[ ▶ プロフィールを表示]({message_link})",
            color=embed_color
        )
        embed.set_author(
            name=f'{display_name} が 入室したよ！',
            icon_url=member.display_avatar.url
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        debug_log(f"[MESSAGE LINK] `{display_name}` のメッセージリンクを埋め込み形式で転記: {message_link}")
        sent_msg = await target_channel.send(embed=embed)

        # 🔽 JSONファイルに保存
        self.profile_message_map[str(member.id)] = {
            "channel_id": str(target_channel.id),
            "message_id": str(sent_msg.id)
        }
        save_profile_messages(self.profile_message_map)

    async def delete_all_messages_from_channel(self, target_channel):
        """指定されたテキストチャンネルのメッセージをすべて一括削除する（14日以内のみ対象）"""
        while True:
            # 最大100件取得（14日以内）
            messages = [msg async for msg in target_channel.history(limit=100)]
            if not messages:
                break
            try:
                await target_channel.delete_messages(messages)
                await asyncio.sleep(1)  # レートリミット対策
            except discord.HTTPException as e:
                print(f"[ERROR] bulk_delete failed: {e}")
                break

async def setup(bot):
    await bot.add_cog(VoiceEventsCog(bot))
