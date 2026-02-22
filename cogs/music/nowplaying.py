from __future__ import annotations

from discord.ext import commands

from core.cleanup import reply_and_cleanup


class NowPlayingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="nowplaying", description="Show current song")
    async def nowplaying(self, ctx: commands.Context) -> None:
        if not ctx.guild or not hasattr(self.bot, "music_states"):
            await reply_and_cleanup(ctx, "Nothing is playing.")
            return

        state = self.bot.music_states.get(ctx.guild.id)
        if not state or not state.now_playing:
            await reply_and_cleanup(ctx, "Nothing is playing.")
            return

        track = state.now_playing
        await reply_and_cleanup(ctx, f"Now playing: **{track.title}** - {track.artist}\n{track.page_url}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NowPlayingCog(bot))
