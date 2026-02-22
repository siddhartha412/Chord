from __future__ import annotations

from discord.ext import commands

from core.cleanup import reply_and_cleanup


class QueueCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="queue", description="Show queue")
    async def queue(self, ctx: commands.Context) -> None:
        if not ctx.guild or not hasattr(self.bot, "music_states"):
            await reply_and_cleanup(ctx, "Queue is empty.")
            return

        state = self.bot.music_states.get(ctx.guild.id)
        if not state:
            await reply_and_cleanup(ctx, "Queue is empty.")
            return

        lines: list[str] = []
        if state.now_playing:
            lines.append(f"Now: **{state.now_playing.title}** - {state.now_playing.artist}")

        if not state.queue:
            if lines:
                lines.append("Up next: empty")
                await reply_and_cleanup(ctx, "\n".join(lines))
                return
            await reply_and_cleanup(ctx, "Queue is empty.")
            return

        lines.append("Up next:")
        for i, track in enumerate(list(state.queue)[:10], start=1):
            lines.append(f"{i}. {track.title} - {track.artist}")

        remaining = len(state.queue) - 10
        if remaining > 0:
            lines.append(f"...and {remaining} more")

        await reply_and_cleanup(ctx, "\n".join(lines))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(QueueCog(bot))
