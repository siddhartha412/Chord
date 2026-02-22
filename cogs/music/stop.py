from __future__ import annotations

from discord.ext import commands

from core.cleanup import reply_and_cleanup


class StopCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="stop", description="Stop music and clear queue")
    async def stop(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            await reply_and_cleanup(ctx, "Use this command in a server.")
            return

        state = None
        if hasattr(self.bot, "music_states") and ctx.guild.id in self.bot.music_states:
            state = self.bot.music_states[ctx.guild.id]
            state.queue.clear()
            state.now_playing = None
            if state.worker_task and not state.worker_task.done():
                state.worker_task.cancel()
            state.worker_task = None

        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_connected():
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()
            if state and state.mode_247:
                play_cog = self.bot.get_cog("PlayCog")
                if play_cog:
                    await play_cog._play_most_popular_for_guild(ctx.guild)
                await reply_and_cleanup(
                    ctx,
                    "Stopped current playback. 24/7 is enabled, so I stayed connected.",
                )
                return
            await voice_client.disconnect()

        await reply_and_cleanup(ctx, "Stopped playback and cleared queue.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StopCog(bot))
