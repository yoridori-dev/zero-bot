# cogs/ogiri.py
import math
from typing import Dict, Optional, Set, List

import discord
from discord.ext import commands
from discord import app_commands

from config import (
    OGIRI_PROMPT_CHANNEL_ID,
    ALLOWED_DEST_CHANNEL_IDS,
    OGIRI_CONTROL_MESSAGE,
    OGIRI_POST_TITLE,
    OGIRI_FOOTER_PREFIX,
)

SELECT_PAGE_SIZE = 25  # DiscordのSelect options上限

class Ogiri(commands.Cog):
    """大喜利：モーダルで本文入力 → エフェメラルUIで宛先複数選択 → 一括投下"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # user_id -> {"author": str, "content": str}
        self.pending: Dict[int, Dict[str, str]] = {}

    # ------- ユーティリティ -------
    def collect_candidate_channels(self, guild: discord.Guild) -> List[discord.TextChannel]:
        """ホワイトリスト or 送信権限のある全テキストチャンネルを候補化"""
        ids = [int(x) for x in ALLOWED_DEST_CHANNEL_IDS] if ALLOWED_DEST_CHANNEL_IDS else None
        chans = [ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages]
        if ids:
            allowed = set(ids)
            chans = [ch for ch in chans if ch.id in allowed]
        # 表示順をカテゴリ→positionで安定化
        chans.sort(key=lambda c: (c.category.position if c.category else -1, c.position))
        return chans

    # ------- 永続ビューの登録（Bot起動後もボタンが生きる） -------
    async def cog_load(self):
        self.bot.add_view(OgiriControlView(self))  # 永続ビュー

    # ------- /ogiri_setup: コントロールメッセージを設置 -------
    @app_commands.command(name="ogiri_setup", description="大喜利コントロールメッセージを設置（管理者のみ）")
    async def ogiri_setup(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("ギルド管理者のみ実行できます。", ephemeral=True)
            return

        ch = interaction.guild.get_channel(OGIRI_PROMPT_CHANNEL_ID)
        if not isinstance(ch, discord.TextChannel):
            await interaction.response.send_message("OGIRI_PROMPT_CHANNEL_ID がテキストチャンネルではありません。", ephemeral=True)
            return

        view = OgiriControlView(self)
        msg = await ch.send(OGIRI_CONTROL_MESSAGE, view=view)
        await interaction.response.send_message(f"設置しました: {ch.mention} / message_id={msg.id}", ephemeral=True)

# ================== UI定義 ==================

class OgiriControlView(discord.ui.View):
    """出題ボタン付きのコントロールビュー（永続）"""
    def __init__(self, cog: Ogiri, timeout: Optional[float] = None):
        super().__init__(timeout=timeout)
        self.cog = cog

    @discord.ui.button(label="出題する", style=discord.ButtonStyle.primary, custom_id="ogiri:start")
    async def start_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(OgiriModal(self.cog))

class OgiriModal(discord.ui.Modal, title="お題を作成"):
    """モーダル：文字入力のみ（出題者・お題本文）"""
    def __init__(self, cog: Ogiri):
        super().__init__()
        self.cog = cog

        self.author_input = discord.ui.TextInput(
            label="出題者（表示名）", placeholder="おなまえ", required=True, max_length=50
        )
        self.content_input = discord.ui.TextInput(
            label="お題（本文）",
            style=discord.TextStyle.paragraph,
            placeholder="例）『こんなAIアシスタントは嫌だ』どんなの？",
            required=True, max_length=1000
        )

        # モーダルに項目を登録
        self.add_item(self.author_input)
        self.add_item(self.content_input)

    async def on_submit(self, interaction: discord.Interaction):
        assert interaction.guild
        uid = interaction.user.id

        # 一時データを保存
        self.cog.pending[uid] = {
            "author": str(self.author_input.value).strip(),
            "content": str(self.content_input.value).strip(),
        }

        # 宛先候補を収集（ホワイトリスト優先、なければ全テキスト）
        candidates = self.cog.collect_candidate_channels(interaction.guild)
        if not candidates:
            await interaction.response.send_message("投下可能なチャンネルが見つからないよ。", ephemeral=True)
            return

        view = DestinationSelectView(cog=self.cog, guild=interaction.guild, user_id=uid, candidates=candidates)
        await interaction.response.send_message(
            "投下先チャンネルを選んで「投下」を押してね（複数可・ページ切替可）",
            view=view,
            ephemeral=True
        )

class ChannelPageSelect(discord.ui.Select):
    """1ページ分の候補（最大25件）を表示するSelect"""
    def __init__(self, page_items: List[discord.TextChannel], already: Set[int]):
        options = []
        for ch in page_items:
            label = f"#{ch.name}"
            desc = ch.category.name if ch.category else "No Category"
            options.append(discord.SelectOption(
                label=label,
                value=str(ch.id),
                description=desc,
                default=(ch.id in already),
            ))
        super().__init__(
            placeholder="チャンネルを選択（複数可）",
            min_values=0,  # ページ切替だけしたい時もあるので0許可
            max_values=len(options) or 1,
            options=options,
            custom_id="ogiri:dest_select"
        )

class DestinationSelectView(discord.ui.View):
    """モーダル後に出る：宛先選択（複数）＋ ページング ＋ 投下/キャンセル"""
    def __init__(self, cog: Ogiri, guild: discord.Guild, user_id: int,
                 candidates: List[discord.TextChannel], timeout: Optional[float] = 600):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.guild = guild
        self.user_id = user_id
        self.candidates = candidates
        self.page = 0
        self.selected: Set[int] = set()
        self.pages = math.ceil(len(self.candidates) / SELECT_PAGE_SIZE)
        self._refresh_select()

    # 現在ページの候補スライス
    def _get_page_slice(self) -> List[discord.TextChannel]:
        start = self.page * SELECT_PAGE_SIZE
        end = start + SELECT_PAGE_SIZE
        return self.candidates[start:end]

    # Selectの差し替え
    def _refresh_select(self):
        for item in list(self.children):
            if isinstance(item, discord.ui.Select):
                self.remove_item(item)
        self.add_item(ChannelPageSelect(self._get_page_slice(), self.selected))

    # Selectの選択イベント
    @discord.ui.select(custom_id="ogiri:dest_select")
    async def on_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これは他の人の出題です。自分で開始してね！", ephemeral=True)
            return
        # 現ページに含まれるIDを一旦除去してトグル更新
        page_ids = {c.id for c in self._get_page_slice()}
        self.selected -= page_ids
        for v in select.values:
            try:
                cid = int(v)
                self.selected.add(cid)
            except ValueError:
                pass
        await interaction.response.defer()  # 表示は据え置き

    # ページング（前）
    @discord.ui.button(label="← 前へ", style=discord.ButtonStyle.secondary, custom_id="ogiri:prev")
    async def prev_page(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これは他の人の出題です。自分で開始してね！", ephemeral=True)
            return
        if self.page > 0:
            self.page -= 1
            self._refresh_select()
            await interaction.response.edit_message(view=self)

    # ページング（次）
    @discord.ui.button(label="次へ →", style=discord.ButtonStyle.secondary, custom_id="ogiri:next")
    async def next_page(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これは他の人の出題です。自分で開始してね！", ephemeral=True)
            return
        if self.page < self.pages - 1:
            self.page += 1
            self._refresh_select()
            await interaction.response.edit_message(view=self)

    # 投下
    @discord.ui.button(label="投下", style=discord.ButtonStyle.success, custom_id="ogiri:post")
    async def post_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これは他の人の出題です。自分で開始してね！", ephemeral=True)
            return

        payload = self.cog.pending.get(self.user_id)
        if not payload:
            await interaction.response.send_message("一時データが見つからないよ。最初からやり直して！", ephemeral=True)
            return

        if not self.selected:
            await interaction.response.send_message("投下先が選ばれていないよ。最低1つ選んでね。", ephemeral=True)
            return

        embed = discord.Embed(title=OGIRI_POST_TITLE, description=payload["content"])
        embed.set_footer(text=f"{OGIRI_FOOTER_PREFIX}{payload['author']}")

        sent, failed = [], []
        for cid in list(self.selected):
            ch = self.guild.get_channel(cid)
            if isinstance(ch, discord.TextChannel):
                try:
                    await ch.send(embed=embed)
                    sent.append(cid)
                except Exception:
                    failed.append(cid)
            else:
                failed.append(cid)

        # 後片付け
        self.cog.pending.pop(self.user_id, None)
        self.clear_items()
        msg = f"✅ 投下完了：{len(sent)}件"
        if failed:
            msg += f"\n⚠ 失敗: {', '.join(f'<#{i}>' for i in failed)}"
        await interaction.response.edit_message(content=msg, view=None)

    # キャンセル
    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary, custom_id="ogiri:cancel")
    async def cancel_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これは他の人の出題です。自分で開始してね！", ephemeral=True)
            return
        self.cog.pending.pop(self.user_id, None)
        await interaction.response.edit_message(content="キャンセルしました。", view=None)


# ---- Cogセットアップエントリ ----
async def setup(bot: commands.Bot):
    await bot.add_cog(Ogiri(bot))
