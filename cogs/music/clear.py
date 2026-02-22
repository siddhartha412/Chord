from __future__ import annotations

from discord.ext import commands

from core.cleanup import reply_and_cleanup


class ClearCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="clear", description="Clear queued songs")
    async def clear(self, ctx: commands.Context) -> None:
        if not ctx.guild or not hasattr(self.bot, "music_states"):
            await reply_and_cleanup(ctx, "Queue is already empty.")
            return

        state = self.bot.music_states.get(ctx.guild.id)
        if not state or not state.queue:
            await reply_and_cleanup(ctx, "Queue is already empty.")
            return

        count = len(state.queue)
        state.queue.clear()
        await reply_and_cleanup(ctx, f"Cleared {count} queued song(s).")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ClearCog(bot))
