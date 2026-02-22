from __future__ import annotations

import asyncio
import json
from pathlib import Path

import discord
from discord.ext import commands

from core.cleanup import delete_message_by_id, make_embed, reply_and_cleanup
from core.jiosaavn import JioSaavnClient
from core.music_state import GuildMusicState, Track


def _format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "Unknown"
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


class PlayerControls(discord.ui.View):
    def __init__(self, cog: "PlayCog", guild_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id

    async def _guild_voice(self) -> tuple[discord.Guild | None, discord.VoiceClient | None]:
        guild = self.cog.bot.get_guild(self.guild_id)
        if not guild:
            return None, None
        return guild, guild.voice_client

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.secondary)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        guild, voice = await self._guild_voice()
        if not guild or not voice or not voice.is_connected():
            await interaction.response.send_message("I am not in a voice channel.", ephemeral=True)
            return

        if voice.is_paused():
            voice.resume()
            button.label = "Pause"
            await interaction.response.edit_message(view=self)
            return

        if voice.is_playing():
            voice.pause()
            button.label = "Resume"
            await interaction.response.edit_message(view=self)
            return

        await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.primary)
    async def skip(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        guild, voice = await self._guild_voice()
        if not guild or not voice or not voice.is_connected() or (not voice.is_playing() and not voice.is_paused()):
            await interaction.response.send_message("Nothing to skip.", ephemeral=True)
            return
        voice.stop()
        await interaction.response.send_message("Skipped.", ephemeral=True)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        guild, voice = await self._guild_voice()
        if not guild or not voice or not voice.is_connected():
            await interaction.response.send_message("I am not in a voice channel.", ephemeral=True)
            return

        state = self.cog._state(self.guild_id)
        state.queue.clear()
        state.now_playing = None

        if voice.is_playing() or voice.is_paused():
            voice.stop()

        if state.mode_247:
            await self.cog._play_most_popular_for_guild(guild)
            await interaction.response.send_message(
                "Stopped current playback. 24/7 is enabled, so I will stay connected.",
                ephemeral=True,
            )
            return

        await voice.disconnect()
        await interaction.response.send_message("Stopped and disconnected.", ephemeral=True)


class PlayCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.jiosaavn = JioSaavnClient(bot.jiosaavn_base_url)
        self.now_playing_emoji_id = self._load_now_playing_emoji_id()
        if not hasattr(self.bot, "music_states"):
            self.bot.music_states = {}

    @staticmethod
    def _load_now_playing_emoji_id() -> int | None:
        config_path = Path("emoji.json")
        if not config_path.exists():
            return None

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        raw = (
            data.get("now_playing_emoji_id")
            or data.get("now_playing")
            or data.get("now_playing_title_emoji_id")
        )
        if raw is None:
            return None
        text = str(raw).strip()
        return int(text) if text.isdigit() else None

    def _now_playing_title(self) -> str:
        if not self.now_playing_emoji_id:
            return "Now Playing"

        emoji = self.bot.get_emoji(self.now_playing_emoji_id)
        if emoji:
            return f"{emoji} Now Playing"

        return f"<:np:{self.now_playing_emoji_id}> Now Playing"

    def _state(self, guild_id: int) -> GuildMusicState:
        if guild_id not in self.bot.music_states:
            self.bot.music_states[guild_id] = GuildMusicState()
        return self.bot.music_states[guild_id]

    async def _send_to_channel(self, guild: discord.Guild, message: str) -> discord.Message | None:
        state = self._state(guild.id)
        if not state.text_channel_id:
            return None

        channel = self.bot.get_channel(state.text_channel_id)
        if isinstance(channel, discord.abc.Messageable):
            try:
                sent = await channel.send(embed=make_embed(message))
                return sent
            except Exception as exc:
                print(f"Failed to send message in guild {guild.id}: {exc}")
        return None

    async def _send_now_playing(self, guild: discord.Guild, track: Track) -> discord.Message | None:
        state = self._state(guild.id)
        if not state.text_channel_id:
            return None

        channel = self.bot.get_channel(state.text_channel_id)
        if not isinstance(channel, discord.abc.Messageable):
            return None

        embed = discord.Embed(
            title=self._now_playing_title(),
            description=f"**{track.title}** - {track.artist}",
        )
        embed.add_field(name="Duration", value=_format_duration(track.duration), inline=True)
        embed.add_field(name="Source", value=f"[JioSaavn]({track.page_url})", inline=True)
        if track.image_url:
            embed.set_thumbnail(url=track.image_url)

        view = PlayerControls(self, guild.id)
        try:
            return await channel.send(embed=embed, view=view)
        except Exception as exc:
            print(f"Failed to send now-playing embed in guild {guild.id}: {exc}")
            return None

    async def _start_next_track(self, guild: discord.Guild) -> None:
        state = self._state(guild.id)
        voice_client = guild.voice_client

        if not voice_client or not voice_client.is_connected():
            state.now_playing = None
            return

        if not state.queue:
            state.now_playing = None
            return

        track = state.queue.popleft()
        state.now_playing = track

        try:
            source = discord.FFmpegOpusAudio(
                track.stream_url,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn",
            )
        except Exception as exc:
            state.now_playing = None
            await self._send_to_channel(guild, f"Playback failed: `{exc}`")
            return

        def after_play(err: Exception | None) -> None:
            fut = asyncio.run_coroutine_threadsafe(
                self._after_track_finished(guild.id, err),
                self.bot.loop,
            )
            try:
                fut.result(timeout=10)
            except Exception as callback_exc:
                print(f"after_play callback failed for guild {guild.id}: {callback_exc}")

        try:
            voice_client.play(source, after=after_play)
        except Exception as exc:
            state.now_playing = None
            await self._send_to_channel(guild, f"Playback failed: `{exc}`")
            return

        sent = await self._send_now_playing(guild, track)
        if sent:
            state.now_playing_channel_id = sent.channel.id
            state.now_playing_message_id = sent.id

    async def _after_track_finished(self, guild_id: int, err: Exception | None) -> None:
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        if err:
            print(f"Playback error in guild {guild_id}: {err}")

        state = self._state(guild_id)
        finished_track = state.now_playing

        # Record play count for finished track
        if finished_track:
            play_count = state.record_play(finished_track)
            print(f"Track '{finished_track.title}' played {play_count} times")

        await delete_message_by_id(self.bot, state.now_playing_channel_id, state.now_playing_message_id)
        if finished_track:
            await delete_message_by_id(
                self.bot,
                finished_track.request_channel_id,
                finished_track.request_message_id,
            )
        state.now_playing = None
        state.now_playing_channel_id = None
        state.now_playing_message_id = None

        # Handle 24/7 mode - auto-play most popular if queue is empty
        if state.mode_247 and not state.queue:
            await self._play_most_popular_for_guild(guild)

        await self._start_next_track(guild)

    async def _play_most_popular_for_guild(self, guild: discord.Guild) -> None:
        """Fetch and queue most popular songs for 24/7 mode."""
        state = self._state(guild.id)

        # Get popular track IDs
        popular_ids = state.get_most_played_tracks(limit=10)

        if not popular_ids:
            # No history yet, search for popular Hindi songs
            popular_queries = ["Bollywood Hits", "Arijit Singh", "Neha Kakkar", "Badshah", "Honey Singh"]
            import random
            query = random.choice(popular_queries)
            track = await self.jiosaavn.search_first_track(self.bot.http_session, query)
            if track:
                state.queue.append(track)
            return

        # Fetch tracks by their IDs (search by title/URL fragment)
        for track_id in popular_ids[:5]:  # Top 5
            # Search for the track
            track = await self.jiosaavn.search_first_track(self.bot.http_session, track_id)
            if track:
                state.queue.append(track)

    @commands.hybrid_command(name="play", description="Play a song from JioSaavn")
    async def play(self, ctx: commands.Context, *, query: str) -> None:
        if not ctx.guild:
            await reply_and_cleanup(ctx, "Use this command in a server.")
            return

        if not ctx.author.voice or not ctx.author.voice.channel:
            await reply_and_cleanup(ctx, "Join a voice channel first.")
            return

        voice_client = ctx.voice_client
        if voice_client is None:
            voice_client = await ctx.author.voice.channel.connect()
        elif voice_client.channel != ctx.author.voice.channel:
            await voice_client.move_to(ctx.author.voice.channel)

        if not self.bot.http_session:
            await reply_and_cleanup(ctx, "HTTP session is not ready.")
            return

        track = await self.jiosaavn.search_first_track(self.bot.http_session, query)
        if not track:
            await reply_and_cleanup(ctx, "No result found for that query.")
            return

        state = self._state(ctx.guild.id)
        state.text_channel_id = ctx.channel.id
        if ctx.message is not None:
            track.request_channel_id = ctx.channel.id
            track.request_message_id = ctx.message.id
        state.queue.append(track)

        if voice_client.is_playing() or voice_client.is_paused() or state.now_playing:
            await reply_and_cleanup(
                ctx, f"Queued: **{track.title}** - {track.artist} (position {len(state.queue)})"
            )
            return

        await self._start_next_track(ctx.guild)

    @commands.hybrid_command(name="sortqueue", description="Sort queue by play count (most played first)")
    async def sort_queue(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            await reply_and_cleanup(ctx, "Use this command in a server.")
            return

        state = self._state(ctx.guild.id)
        if not state.queue:
            await reply_and_cleanup(ctx, "Queue is empty.")
            return

        if len(state.queue) < 2:
            await reply_and_cleanup(ctx, "Need at least 2 songs to sort.")
            return

        state.sort_queue_by_play_count()
        await reply_and_cleanup(ctx, f"Queue sorted by play count! {len(state.queue)} songs reordered.")

    @commands.hybrid_command(name="popular", description="Show most played songs")
    async def popular(self, ctx: commands.Context, limit: int = 10) -> None:
        if not ctx.guild:
            await reply_and_cleanup(ctx, "Use this command in a server.")
            return

        state = self._state(ctx.guild.id)
        top_tracks = state.play_count_manager.get_all_sorted(min(limit, 20))

        if not top_tracks:
            await reply_and_cleanup(ctx, "No play history yet! Play some songs first.")
            return

        lines = ["**Most Played Songs:**"]
        for i, (track_id, count) in enumerate(top_tracks, 1):
            lines.append(f"{i}. `{track_id}` - {count} plays")

        await reply_and_cleanup(ctx, "\n".join(lines))

    @commands.hybrid_command(name="playcount", description="Show play count for current song")
    async def play_count(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            await reply_and_cleanup(ctx, "Use this command in a server.")
            return

        state = self._state(ctx.guild.id)

        if state.now_playing:
            count = state.get_play_count(state.now_playing)
            await reply_and_cleanup(ctx, f"**{state.now_playing.title}** has been played **{count}** times.")
            return

        if state.queue:
            first = state.queue[0]
            count = state.get_play_count(first)
            await reply_and_cleanup(ctx, f"Next up: **{first.title}** - played **{count}** times.")
            return

        await reply_and_cleanup(ctx, "Nothing is playing or queued.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PlayCog(bot))
