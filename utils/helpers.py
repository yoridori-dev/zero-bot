import discord
from discord import app_commands
import re

def normalize_voice_channel_name(name):
    """ボイスチャンネル名を比較用に正規化"""
    return re.sub(r'\s+', ' ', name).strip()

def normalize_text_channel_name(name):
    """テキストチャンネル名を比較用に正規化"""
    return re.sub(r'\s+', '-', name.strip())

async def voice_users_autocomplete(interaction: discord.Interaction, current: str):
    """ボイスチャンネルのユーザーをオートコンプリート"""
    guild = interaction.guild
    if guild is None:
        return []

    voice_members = [
        member.display_name for vc in guild.voice_channels for member in vc.members if current.lower() in member.display_name.lower()
    ]
    return [app_commands.Choice(name=name, value=name) for name in voice_members[:25]]
