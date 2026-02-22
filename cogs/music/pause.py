from __future__ import annotations

from discord.ext import commands

from core.cleanup import reply_and_cleanup


class PauseCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="pause", description="Pause current song")
    async def pause(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            await reply_and_cleanup(ctx, "Use this command in a server.")
            return

        voice_client = ctx.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            await reply_and_cleanup(ctx, "I am not in a voice channel.")
            return

        if not voice_client.is_playing():
            await reply_and_cleanup(ctx, "Nothing is playing.")
            return

        voice_client.pause()
        await reply_and_cleanup(ctx, "Paused.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PauseCog(bot))
