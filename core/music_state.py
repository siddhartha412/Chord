from __future__ import annotations

import asyncio
import json
import os
from collections import deque
from dataclasses import dataclass
from typing import Deque, ClassVar


@dataclass(slots=True)
class Track:
    title: str
    stream_url: str
    page_url: str
    artist: str
    duration: int
    image_url: str | None = None
    request_channel_id: int | None = None
    request_message_id: int | None = None
    play_count: int = 0


class PlayCountManager:
    """Manages persistent play count storage across bot restarts."""

    _instance: ClassVar[PlayCountManager | None] = None
    _data: ClassVar[dict[str, int]] = {}
    _file_path: ClassVar[str] = "data/play_counts.json"

    def __new__(cls) -> PlayCountManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._load()
        return cls._instance

    @classmethod
    def _load(cls) -> None:
        """Load play counts from file."""
        os.makedirs(os.path.dirname(cls._file_path), exist_ok=True)
        if os.path.exists(cls._file_path):
            try:
                with open(cls._file_path, "r") as f:
                    cls._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                cls._data = {}
        else:
            cls._data = {}

    @classmethod
    def _save(cls) -> None:
        """Save play counts to file."""
        os.makedirs(os.path.dirname(cls._file_path), exist_ok=True)
        with open(cls._file_path, "w") as f:
            json.dump(cls._data, f, indent=2)

    def increment(self, track_id: str) -> int:
        """Increment play count for a track and return new count."""
        self._data[track_id] = self._data.get(track_id, 0) + 1
        self._save()
        return self._data[track_id]

    def get(self, track_id: str) -> int:
        """Get play count for a track."""
        return self._data.get(track_id, 0)

    def get_all_sorted(self, limit: int = 100) -> list[tuple[str, int]]:
        """Get all tracks sorted by play count (highest first)."""
        sorted_tracks = sorted(self._data.items(), key=lambda x: x[1], reverse=True)
        return sorted_tracks[:limit]

    def get_top_track_ids(self, limit: int = 10) -> list[str]:
        """Get top track IDs by play count."""
        return [track_id for track_id, _ in self.get_all_sorted(limit)]


class GuildMusicState:
    def __init__(self) -> None:
        self.queue: Deque[Track] = deque()
        self.now_playing: Track | None = None
        self.worker_task: asyncio.Task | None = None
        self.text_channel_id: int | None = None
        self.now_playing_channel_id: int | None = None
        self.now_playing_message_id: int | None = None
        self.mode_247: bool = False
        self.voice_channel_id: int | None = None
        self.play_count_manager = PlayCountManager()

    def get_track_id(self, track: Track) -> str:
        """Generate unique ID for a track based on URL."""
        return track.page_url.split("/")[-1] if "/" in track.page_url else track.title

    def record_play(self, track: Track) -> int:
        """Record a play for a track and return the new play count."""
        track_id = self.get_track_id(track)
        return self.play_count_manager.increment(track_id)

    def get_play_count(self, track: Track) -> int:
        """Get play count for a track."""
        track_id = self.get_track_id(track)
        return self.play_count_manager.get(track_id)

    def get_most_played_tracks(self, limit: int = 10) -> list[Track]:
        """Get most played tracks as Track objects (returns empty list - needs to be populated from search)."""
        # This returns track IDs, actual tracks need to be searched/retrieved
        return self.play_count_manager.get_top_track_ids(limit)

    def sort_queue_by_play_count(self) -> None:
        """Sort the current queue by play count (highest first)."""
        tracks_with_counts = [(track, self.get_play_count(track)) for track in self.queue]
        tracks_with_counts.sort(key=lambda x: x[1], reverse=True)
        self.queue.clear()
        for track, _ in tracks_with_counts:
            self.queue.append(track)
