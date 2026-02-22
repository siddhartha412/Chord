from __future__ import annotations

from discord.ext import commands

from core.cleanup import reply_and_cleanup


class PingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Show bot latency")
    async def ping(self, ctx: commands.Context) -> None:
        latency_ms = round(self.bot.latency * 1000)
        await reply_and_cleanup(ctx, f"Pong! `{latency_ms}ms`")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PingCog(bot))
