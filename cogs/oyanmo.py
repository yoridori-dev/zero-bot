import discord
from discord import app_commands
from discord.ext import commands
from utils.helpers import voice_users_autocomplete
from utils.countdown import countdown_procedure, countdown_active
from utils.messages import get_random_success_message
from config import TARGET_VOICE_CHANNEL_ID

class OyanmoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="おやんも", description="指定したユーザーを寝落ち部屋に移動させます")
    @app_commands.autocomplete(username=voice_users_autocomplete)
    async def おやんも(self, interaction: discord.Interaction, username: str, countdown: bool = False):
        await interaction.response.defer()

        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("サーバー情報を取得できません。", ephemeral=True)
            return

        target_member = discord.utils.find(lambda m: m.display_name == username, guild.members)
        if target_member is None or target_member.voice is None:
            await interaction.followup.send(f"❌ `{username}` はボイスチャンネルにいません。")
            return

        target_channel = interaction.client.get_channel(TARGET_VOICE_CHANNEL_ID)
        if not isinstance(target_channel, discord.VoiceChannel):
            await interaction.followup.send(f"❌ `{username}`: 指定されたボイスチャンネルが見つかりません。")
            return

        # 初期表示
        embed = discord.Embed(
            title="おやんも実行",
            description=f"`{target_member.display_name}` を寝落ち部屋へ移動させます。",
            color=0x5865F2
        )
        response_message = await interaction.followup.send(embed=embed, wait=True)

        if countdown:
            await countdown_procedure(interaction, target_member, target_channel, response_message)

        else:
            await target_member.move_to(target_channel)
            embed.description = get_random_success_message(target_member.display_name)
            embed.color = 0x32CD32
            await response_message.edit(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(OyanmoCog(bot))
