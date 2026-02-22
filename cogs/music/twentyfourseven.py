from __future__ import annotations

import asyncio
from typing import ClassVar

import discord
from discord.ext import commands

from core.cleanup import delete_message_by_id, make_embed, reply_and_cleanup
from core.music_state import GuildMusicState


class TwentyFourSevenCog(commands.Cog):
    """24/7 mode - keeps bot in voice channel and auto-plays most popular songs."""

    _247_guilds: ClassVar[set[int]] = set()

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not hasattr(self.bot, "music_states"):
            self.bot.music_states = {}

    def _state(self, guild_id: int) -> GuildMusicState:
        if guild_id not in self.bot.music_states:
            self.bot.music_states[guild_id] = GuildMusicState()
        return self.bot.music_states[guild_id]

    @commands.hybrid_command(name="247", description="Toggle 24/7 mode - bot stays in voice and auto-plays popular songs")
    async def twenty_four_seven(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            await reply_and_cleanup(ctx, "Use this command in a server.")
            return

        if not ctx.author.voice or not ctx.author.voice.channel:
            await reply_and_cleanup(ctx, "Join a voice channel first.")
            return

        guild_id = ctx.guild.id
        voice_client = ctx.voice_client

        if guild_id in self._247_guilds:
            # Disable 24/7 mode
            self._247_guilds.discard(guild_id)
            state = self._state(guild_id)
            state.mode_247 = False
            state.voice_channel_id = None
            if voice_client and voice_client.is_connected():
                await voice_client.disconnect()
            await reply_and_cleanup(ctx, "24/7 mode disabled. Bot will leave when queue is empty.")
            return

        # Enable 24/7 mode
        self._247_guilds.add(guild_id)
        state = self._state(guild_id)
        state.mode_247 = True
        state.voice_channel_id = ctx.author.voice.channel.id
        state.text_channel_id = ctx.channel.id

        if voice_client is None:
            voice_client = await ctx.author.voice.channel.connect()
        elif voice_client.channel != ctx.author.voice.channel:
            await voice_client.move_to(ctx.author.voice.channel)

        await reply_and_cleanup(ctx, "24/7 mode enabled! Bot will stay in voice channel and auto-play most popular songs when queue is empty.")

        # Start auto-play if nothing is playing
        if not voice_client.is_playing() and not voice_client.is_paused():
            await self._play_most_popular(ctx.guild)

    async def _play_most_popular(self, guild: discord.Guild) -> None:
        """Play the most popular song based on play count."""
        from cogs.music.play import PlayCog
        from core.jiosaavn import JioSaavnClient

        play_cog = self.bot.get_cog("PlayCog")
        if not isinstance(play_cog, PlayCog):
            return

        state = self._state(guild.id)
        if not state.mode_247:
            return

        # Get most popular tracks from play history
        popular_tracks = state.get_most_played_tracks(limit=10)

        voice_client = guild.voice_client
        if not voice_client or not voice_client.is_connected():
            return

        # Add popular tracks to queue
        for track in popular_tracks:
            state.queue.append(track)

        # Start playing if not already
        if not voice_client.is_playing() and not voice_client.is_paused() and not state.now_playing:
            await play_cog._start_next_track(guild)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        """Handle voice state changes for 24/7 mode."""
        if member.bot:
            return

        guild = member.guild
        if guild.id not in self._247_guilds:
            return

        voice_client = guild.voice_client
        if not voice_client or not voice_client.is_connected():
            return

        # Check if bot is alone in channel
        channel = voice_client.channel
        non_bot_members = [m for m in channel.members if not m.bot]

        if len(non_bot_members) == 0:
            # Everyone left, but in 24/7 mode we stay and play most popular
            state = self._state(guild.id)
            if not state.queue and not state.now_playing:
                await self._play_most_popular(guild)

    async def handle_track_finished(self, guild: discord.Guild) -> None:
        """Called when a track finishes - auto-play next popular song in 24/7 mode."""
        if guild.id not in self._247_guilds:
            return

        state = self._state(guild.id)
        voice_client = guild.voice_client

        if not voice_client or not voice_client.is_connected():
            return

        # If queue is empty, auto-play most popular
        if not state.queue:
            await self._play_most_popular(guild)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TwentyFourSevenCog(bot))