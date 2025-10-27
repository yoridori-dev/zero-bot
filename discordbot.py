import discord
from discord import app_commands
from discord.ext import commands
import asyncio  # カウントダウン用
import datetime
import os
from dotenv import load_dotenv  # .env からトークンを読み込む
import pytz  # タイムゾーン変換用
import re  # 文字列処理用
import random  # ランダム選択用
# .env ファイルの読み込み
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True  # メッセージの内容取得を有効化
intents.members = True  # メンバー情報取得を有効化
intents.voice_states = True  # ボイスチャンネルの状態変更を監視
intents.guilds = True  # ギルドの情報取得を許可

bot = commands.Bot(command_prefix='!', intents=intents)

CATEGORY_NAME = "インチャテキスト"
TARGET_VOICE_CHANNEL_ID = int(os.getenv("TARGET_VOICE_CHANNEL_ID", "0"))  # .env から取得、デフォルトは 0
STOP_BUTTON_ONLY_COMMAND_USER = os.getenv("STOP_BUTTON_ONLY_COMMAND_USER", "False").lower() == "true"
EXCLUDED_VOICE_CHANNEL_IDS = os.getenv("EXCLUDED_VOICE_CHANNEL_IDS")

voice_text_mapping = {}  # ボイスチャンネルごとのテキストチャンネルを保存する辞書

# JST タイムゾーンを設定
jst = pytz.timezone('Asia/Tokyo')

def normalize_voice_channel_name(name):
    """ボイスチャンネルの名前を比較用に正規化（テキストチャンネルの `-` に対応）"""
    return re.sub(r'\s+', ' ', name).strip()  # 連続するスペースを1つに統一

def normalize_text_channel_name(name):
    """テキストチャンネルの名前を比較用に正規化（ボイスチャンネルの ` ` に対応）"""
    return re.sub(r'\s+', '-', name.strip())  # 連続するスペースを1つの `-` に統一

# **オートコンプリートの関数（デバッグ付き）**
async def voice_users_autocomplete(interaction: discord.Interaction, current: str):
    """現在のサーバーのボイスチャンネルにいるユーザーをリストアップ（デバッグ付き）"""
    guild = interaction.guild  # コマンドを実行したサーバーを取得

    if guild is None:
        print("[DEBUG] サーバー情報が取得できません。")
        return []

    print(f"[DEBUG] サーバー: {guild.name} (ID: {guild.id})")

    # サーバー内のボイスチャンネル（除外IDを除く）を取得
    all_voice_channels = guild.voice_channels
    target_voice_channels = [vc for vc in all_voice_channels if vc.id not in EXCLUDED_VOICE_CHANNEL_IDS]
    print(f"[DEBUG] ボイスチャンネル数: {len(target_voice_channels)}")

    # ボイスチャンネルにいるユーザーの取得
    voice_members = []
    for vc in target_voice_channels:
        print(f"[DEBUG] チャンネル: {vc.name} (ID: {vc.id}) メンバー数: {len(vc.members)}")
        for member in vc.members:
            print(f"[DEBUG] メンバー: {member.display_name} (ID: {member.id})")
            if current.lower() in member.display_name.lower():
                voice_members.append(member.display_name)

    print(f"[DEBUG] 検索結果: {voice_members}")

    return [
        app_commands.Choice(name=name, value=name)
        for name in voice_members[:25]  # Discord の制限により最大 25 件まで
    ]

@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    now = datetime.datetime.now(jst).strftime("%Y%m%d")

    if after.channel is not None and before.channel != after.channel:
        # 入室時
        new_channel_name = f"{now}_{normalize_text_channel_name(after.channel.name)}"

        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)

        if category is None:
            category = await guild.create_category(CATEGORY_NAME)

        # 既存のチャンネルを探す
        target_channel = discord.utils.get(category.text_channels, name=new_channel_name)

        if target_channel is None:
            new_channel = await guild.create_text_channel(new_channel_name, category=category)
            voice_text_mapping[after.channel.id] = new_channel.id  # ID でマッピングを保存
        else:
            new_channel = target_channel
            voice_text_mapping[after.channel.id] = target_channel.id  # 既存チャンネルをマッピング

        embed = discord.Embed(
            description=f"**{member.display_name}**（ID: `{member.id}`）が **{after.channel.name}** に入室しました。",
            color=0x00ff00
        )
        embed.set_author(
            name=f"{member.display_name} さんの入室",
            icon_url=member.display_avatar.url
        )
        embed.set_footer(text=f"{datetime.datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S')}")

        await new_channel.send(embed=embed)

    elif before.channel is not None and after.channel is None:
        # 退室時
        new_channel_name = f"{now}_{normalize_text_channel_name(before.channel.name)}"

        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)

        if category is None:
            category = await guild.create_category(CATEGORY_NAME)

        target_channel = discord.utils.get(category.text_channels, name=new_channel_name)

        if target_channel is None:
            new_channel = await guild.create_text_channel(new_channel_name, category=category)
            voice_text_mapping[before.channel.id] = new_channel.id
        else:
            new_channel = target_channel
            voice_text_mapping[before.channel.id] = target_channel.id

        embed = discord.Embed(
            description=f"**{member.display_name}**（ID: `{member.id}`）が **{before.channel.name}** から退出しました。",
            color=0xff0000
        )
        embed.set_author(
            name=f"{member.display_name} さんの退室",
            icon_url=member.display_avatar.url
        )
        embed.set_footer(text=f"{datetime.datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S')}")

        await new_channel.send(embed=embed)


@bot.event
async def on_message(message):
    now = datetime.datetime.now(jst).strftime("%Y%m%d")

    if message.author.bot:
        return  # ボットのメッセージは無視

    # メッセージがボイスチャンネルのテキストチャットか確認
    if not isinstance(message.channel, discord.VoiceChannel):
        return  # ボイスチャンネルのテキストチャット以外は無視

    # 転記先のテキストチャンネルを探す
    new_channel_name = f"{now}_{normalize_text_channel_name(message.channel.name)}"

    category = discord.utils.get(message.guild.categories, name=CATEGORY_NAME)

    if category is None:
        category = await message.guild.create_category(CATEGORY_NAME)

    target_channel = discord.utils.get(category.text_channels, name=new_channel_name)

    if target_channel is None:
        target_channel = await message.guild.create_text_channel(new_channel_name, category=category)

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
        name=f"{message.author.display_name}   {message_time_jst}",  # 投稿者名 + 投稿日時
        icon_url=message.author.display_avatar.url  # サーバーごとのアバター
    )

    # 1枚目の画像があればセット
    if image_urls:
        embed.set_image(url=image_urls[0])

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

    await bot.process_commands(message)

countdown_lock = asyncio.Lock()
countdown_active = {}

async def set_countdown_active(user_id, value):
    async with countdown_lock:
        countdown_active[user_id] = value
        print(f"[DEBUG] countdown_active[{user_id}] を {value} に変更しました。")

class StopButtonView(discord.ui.View):
    """STOPボタンを提供するView（カウントダウン時のみ表示）"""
    def __init__(self, target_member_id, command_user_id):
        super().__init__(timeout=None)
        self.target_member_id = target_member_id  # ✅ 移動対象のID
        self.command_user_id = command_user_id  # ✅ コマンド実行者のID

    @discord.ui.button(label="STOP", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """STOPボタンが押されたときの処理"""
        if STOP_BUTTON_ONLY_COMMAND_USER and interaction.user.id != self.command_user_id:
            await interaction.response.send_message("❌ あなたにはこのカウントダウンを停止する権限がありません！", ephemeral=True)
            return

        countdown_active[self.target_member_id] = False  # ✅ 移動対象のフラグを更新
        await interaction.response.edit_message(content=f"⏹ `{interaction.user.display_name}` がカウントダウンを停止しました！", view=None)

@bot.tree.command(name="おやんも", description="指定したユーザーを寝落ち部屋に移動させます")
@app_commands.autocomplete(username=voice_users_autocomplete)
async def おやんも(interaction: discord.Interaction, username: str, countdown: bool = False):
    """指定したユーザーを寝落ち部屋に移動させる"""
    await interaction.response.defer()

    guild = interaction.guild
    if guild is None:
        await interaction.followup.send("サーバー情報を取得できません。", ephemeral=True)
        return

    command_user = interaction.user
    channel = interaction.channel

    # 指定ユーザー検索
    target_member = discord.utils.find(lambda m: m.display_name == username, guild.members)
    if target_member is None:
        await interaction.followup.send(f"❌ `{username}`: ユーザーが見つかりません。")
        return
    if target_member.voice is None or target_member.voice.channel is None:
        await interaction.followup.send(f"❌ `{target_member.display_name}` はボイスチャンネルにいません。")
        return

    target_channel = bot.get_channel(TARGET_VOICE_CHANNEL_ID)
    if target_channel is None or not isinstance(target_channel, discord.VoiceChannel):
        await interaction.followup.send(f"❌ `{username}`: 指定されたボイスチャンネルが見つかりません。")
        return

    embed = discord.Embed(
        title="おやんも コマンド実行",
        description=f"🔹 `{command_user.display_name}` が `/おやんも {username}` を実行しました。",
        color=0x5865F2
    )
    embed.set_author(name=command_user.display_name, icon_url=command_user.display_avatar.url)

    # ✅ `countdown=True` の場合のみ STOP ボタンを表示
    if countdown:
        view = StopButtonView(target_member.id, command_user.id)  # ✅ **移動対象 & コマンド実行者のID を設定**
        countdown_msg = await interaction.followup.send(embed=embed, view=view)
    else:
        countdown_msg = await interaction.followup.send(embed=embed)

    countdown_active[target_member.id] = True  # ✅ **移動対象のフラグをセット**

    if countdown:
        for i in range(10, -1, -1):
            if not countdown_active.get(target_member.id, False):  # ✅ **移動対象のフラグを確認**
                embed.description = f"⏹ `{target_member.display_name}` の移動を中止しました！"
                await countdown_msg.edit(embed=embed, view=None)  # ✅ ボタン削除
                return

            embed.description = f"⏳ `{target_member.display_name}` を移動させます: `{i}`"
            await countdown_msg.edit(embed=embed)
            await asyncio.sleep(1)

    if not countdown_active.get(target_member.id, False):  # ✅ **最終チェック**
        embed.description = f"⏹ `{target_member.display_name}` の移動を中止しました！"
        await countdown_msg.edit(embed=embed, view=None)
        return

    await target_member.move_to(target_channel)

    completion_messages = [
                f"✅ いやぁー限界だったねぇ🥰おやんも🌙`{target_member.display_name}` ",
                f"✅ `{target_member.display_name}` すやぴしたの❔きゃわじゃん🥰また明日ね👋🏻",
                f"✅ すーぐ寝るじゃん😪`{target_member.display_name}` いい夢みろよ😘",
                f"✅ え!? `{target_member.display_name}` どゆことぉ？寝たん？ねぇねぇ。",
    ]
    embed.description = random.choice(completion_messages)
    await countdown_msg.edit(embed=embed, view=None)  # ✅ カウントダウン完了後にボタンを削除

    countdown_active[target_member.id] = False  # ✅ フラグをリセット

# **Bot 起動時**
@bot.event
async def on_ready():
    print(f"{bot.user.name} がログインしました！！！ま？それま？")
    try:
        synced = await bot.tree.sync()  # スラッシュコマンドを同期
        print(f"スラッシュコマンドが {len(synced)} 個同期されました。")
    except Exception as e:
        print(f"スラッシュコマンドの同期に失敗しました: {e}")


# **テストコマンド**
@bot.command()
async def zero(ctx):
    await ctx.send('ってわけ！！！')

bot.run(TOKEN)
