from __future__ import annotations

from discord.ext import commands

from core.cleanup import reply_and_cleanup


class LeaveCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="leave", description="Disconnect bot from voice channel")
    async def leave(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            await reply_and_cleanup(ctx, "Use this command in a server.")
            return

        state = getattr(self.bot, "music_states", {}).get(ctx.guild.id)
        if state and state.mode_247:
            await reply_and_cleanup(ctx, "24/7 is enabled. Disable it with `247` first.")
            return

        if state:
            state.queue.clear()
            state.now_playing = None

        voice_client = ctx.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            await reply_and_cleanup(ctx, "I am not in a voice channel.")
            return

        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()

        await voice_client.disconnect()
        await reply_and_cleanup(ctx, "Disconnected.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LeaveCog(bot))
