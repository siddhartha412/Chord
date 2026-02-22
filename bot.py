import asyncio
import os
from pathlib import Path

import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv


class ChordBot(commands.Bot):
    def __init__(self) -> None:
        load_dotenv()

        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True

        prefix = os.getenv("BOT_PREFIX", ";")
        super().__init__(command_prefix=prefix, intents=intents)

        self.http_session: aiohttp.ClientSession | None = None
        jiosaavn_base_url = os.getenv("JIOSAAVN_API_BASE_URL", "").strip()
        if not jiosaavn_base_url:
            raise RuntimeError("JIOSAAVN_API_BASE_URL is missing in .env")
        self.jiosaavn_base_url = jiosaavn_base_url.rstrip("/")
        self.auto_delete_enabled = os.getenv("AUTO_DELETE_ENABLED", "true").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.auto_delete_seconds = max(0, int(os.getenv("AUTO_DELETE_SECONDS", "12")))
        owner_id_raw = os.getenv("OWNER_ID", "").strip()
        if not owner_id_raw.isdigit():
            raise RuntimeError("OWNER_ID is missing or invalid in .env")
        self.owner_id = int(owner_id_raw)
        self.synced_once = False

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))

        for file in Path("cogs").rglob("*.py"):
            if file.name.startswith("_"):
                continue
            ext = ".".join(file.with_suffix("").parts)
            await self.load_extension(ext)

    async def close(self) -> None:
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
        await super().close()


bot = ChordBot()


@bot.event
async def on_ready() -> None:
    if not bot.synced_once:
        await bot.tree.sync()
        bot.synced_once = True

    print(f"Logged in as {bot.user} ({bot.user.id})")


async def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is missing in .env")

    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
