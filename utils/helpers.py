import discord
from discord import app_commands
import re

def normalize_voice_channel_name(name: str) -> str:
    """ボイスチャンネル名を比較用に正規化"""
    original_name = name  # デバッグ用
    name = re.sub(r'\s+', ' ', name).strip()
    print(f"[DEBUG] normalize_voice_channel_name: `{original_name}` → `{name}`")
    return name

def normalize_text_channel_name(name: str) -> str:
    """テキストチャンネル名を比較用に正規化"""
    original_name = name  # デバッグ用
    name = re.sub(r'\s+', '-', name.strip())  # 空白をハイフンに変換
    name = re.sub(r'-+', '-', name)  # 連続するハイフンを1つに統一
    name = name.strip('-')  # 先頭・末尾のハイフンを削除
    print(f"[DEBUG] normalize_text_channel_name: `{original_name}` → `{name}`")
    return name

async def voice_users_autocomplete(interaction: discord.Interaction, current: str):
    """ボイスチャンネルのユーザーをオートコンプリート"""
    guild = interaction.guild
    if guild is None:
        print("[DEBUG] サーバー情報なし")
        return []

    voice_members = []
    for vc in guild.voice_channels:
        for member in vc.members:
            if current.lower() in member.display_name.lower():
                voice_members.append(member.display_name)

    print(f"[DEBUG] オートコンプリート候補: {voice_members[:25]}")

    return [app_commands.Choice(name=name, value=name) for name in voice_members[:25]]
