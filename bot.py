import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from config import TOKEN, intents

load_dotenv()

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} がログインしました！")
    try:
        synced = await bot.tree.sync()
        print(f"🌍 スラッシュコマンドが {len(synced)} 個同期されました。")
    except Exception as e:
        print(f"❌ スラッシュコマンドの同期に失敗: {e}")

async def load_cogs():
    """Cogをロード"""
    for cog in [
        "cogs.oyanmo",
        "cogs.voice_events",
        "cogs.message_handler",
        "cogs.archive_manager",  # ✅ ArchiveManager を追加
    ]:
        try:
            await bot.load_extension(cog)
            print(f"✅ Cog {cog} がロードされました。")
        except Exception as e:
            print(f"❌ Cog {cog} のロードに失敗: {e}")

async def main():
    try:
        async with bot:
            await load_cogs()
            await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Bot が手動で停止されました！")
    finally:
        await bot.close()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot が手動で停止されました！")
    finally:
        loop.close()
