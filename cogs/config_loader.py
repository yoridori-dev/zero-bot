import os
import json
import discord
from discord.ext import commands

class ConfigStore:
    """どこからでも参照できるグローバル設定ストア"""
    def __init__(self) -> None:
        self.data: dict = {}
        self.version: int | None = None

    def load_from_text(self, text: str) -> None:
        cfg = json.loads(text)

        # 必須キーの軽い検証（必要に応じて拡張してね）
        required = ["version"]
        for k in required:
            if k not in cfg:
                raise ValueError(f"config missing key: {k}")

        self.data = cfg
        self.version = cfg.get("version")

    def get(self, path: str, default=None):
        cur = self.data
        for part in path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

# 他のCogから: from cogs.config_loader import config_store
config_store = ConfigStore()


class ConfigLoader(commands.Cog):
    """
    #bot-config（等）のピン留め/直近メッセージ or 添付JSON を読み込む
    - 起動時に自動ロード（失敗してもBotは落とさない）
    - /config reload で再読込
    """
    def __init__(self, bot: commands.Bot, config_channel_id: int) -> None:
        self.bot = bot
        self.config_channel_id = config_channel_id

    async def _fetch_config_text(self) -> str:
        ch = self.bot.get_channel(self.config_channel_id) or await self.bot.fetch_channel(self.config_channel_id)
        if not isinstance(ch, discord.TextChannel):
            raise RuntimeError("Config channel not found or not a text channel")

        # 1) ピン留めを優先
        pins = await ch.pins()
        candidates = pins if pins else [m async for m in ch.history(limit=50)]

        for m in candidates:
            # 本文がJSONなら採用
            try:
                json.loads(m.content)
                return m.content
            except Exception:
                pass

            # JSONファイル添付があれば採用
            for a in m.attachments:
                if a.filename.lower().endswith(".json"):
                    raw = await a.read()
                    return raw.decode("utf-8")

        raise RuntimeError("No valid JSON config found in the channel")

    async def load(self) -> str:
        text = await self._fetch_config_text()
        config_store.load_from_text(text)
        return f"config loaded (version={config_store.version})"

    @commands.hybrid_command(description="設定JSONを再読込します")
    @commands.has_permissions(manage_guild=True)
    async def config_reload(self, ctx: commands.Context):
        try:
            msg = await self.load()
            await ctx.reply(msg, mention_author=False)
        except Exception as e:
            await ctx.reply(f"config reload failed: {e}", mention_author=False)

    @commands.Cog.listener()
    async def on_ready(self):
        # 起動時に読み込み（失敗はログのみ）
        try:
            msg = await self.load()
            print(f"[CONFIG] {msg}")
        except Exception as e:
            print(f"[CONFIG] initial load failed: {e}")


async def setup(bot: commands.Bot):
    # .env などから設定チャンネルIDを取得（未設定なら0→スキップ）
    channel_id = int(os.getenv("CONFIG_CHANNEL_ID", "0"))
    await bot.add_cog(ConfigLoader(bot, channel_id))
