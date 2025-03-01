import asyncio
import discord

countdown_lock = asyncio.Lock()
countdown_active = {}

async def set_countdown_active(user_id, value):
    """カウントダウンの状態を管理"""
    async with countdown_lock:
        countdown_active[user_id] = value
        print(f"[DEBUG] countdown_active[{user_id}] を {value} に変更しました。")

class StopButtonView(discord.ui.View):
    """カウントダウンを停止する STOP ボタン"""
    def __init__(self, target_member_id, command_user_id):
        super().__init__(timeout=None)
        self.target_member_id = target_member_id
        self.command_user_id = command_user_id

    @discord.ui.button(label="STOP", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """STOPボタンを押したときの処理"""
        from config import STOP_BUTTON_ONLY_COMMAND_USER

        if STOP_BUTTON_ONLY_COMMAND_USER and interaction.user.id != self.command_user_id:
            await interaction.response.send_message("❌ あなたにはこのカウントダウンを停止する権限がありません！", ephemeral=True)
            return

        countdown_active[self.target_member_id] = False
        await interaction.response.edit_message(content=f"⏹ `{interaction.user.display_name}` がカウントダウンを停止しました！", view=None)

async def countdown_procedure(interaction, target_member, target_channel):
    """カウントダウンを実行して指定のボイスチャンネルへ移動させる"""
    from utils.messages import completion_messages
    from config import STOP_BUTTON_ONLY_COMMAND_USER

    embed = discord.Embed(
        title="おやんも コマンド実行",
        description=f"🔹 `{interaction.user.display_name}` が `/おやんも {target_member.display_name}` を実行しました。",
        color=0x5865F2
    )
    view = StopButtonView(target_member.id, interaction.user.id)

    countdown_msg = await interaction.followup.send(embed=embed, view=view)

    countdown_active[target_member.id] = True

    for i in range(10, -1, -1):
        if not countdown_active.get(target_member.id, False):
            embed.description = f"⏹ `{target_member.display_name}` の移動を中止しました！"
            await countdown_msg.edit(embed=embed, view=None)
            return

        embed.description = f"⏳ `{target_member.display_name}` を移動させます: `{i}`"
        await countdown_msg.edit(embed=embed)
        await asyncio.sleep(1)

    if not countdown_active.get(target_member.id, False):
        embed.description = f"⏹ `{target_member.display_name}` の移動を中止しました！"
        await countdown_msg.edit(embed=embed, view=None)
        return

    await target_member.move_to(target_channel)

    embed.description = random.choice(completion_messages)
    await countdown_msg.edit(embed=embed, view=None)
    countdown_active[target_member.id] = False
