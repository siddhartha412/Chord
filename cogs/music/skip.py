from __future__ import annotations

from discord.ext import commands

from core.cleanup import reply_and_cleanup


class SkipCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="skip", description="Skip current song")
    async def skip(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            await reply_and_cleanup(ctx, "Use this command in a server.")
            return

        voice_client = ctx.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            await reply_and_cleanup(ctx, "I am not in a voice channel.")
            return

        if not voice_client.is_playing() and not voice_client.is_paused():
            await reply_and_cleanup(ctx, "Nothing is playing.")
            return

        voice_client.stop()
        await reply_and_cleanup(ctx, "Skipped.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SkipCog(bot))
