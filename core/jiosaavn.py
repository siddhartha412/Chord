from __future__ import annotations

import html
from typing import Any
from urllib.parse import urlencode

from core.music_state import Track


class JioSaavnClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def search_first_track(self, session, query: str) -> Track | None:
        results = await self.search_tracks_raw(session, query, limit=20)
        if not results:
            return None

        song = self._select_best_song(results, query)
        if not song:
            return None
        return self.track_from_song(song)

    async def search_tracks_raw(self, session, query: str, limit: int = 20) -> list[dict[str, Any]]:
        params = urlencode({"query": query, "limit": limit, "page": 0})
        url = f"{self.base_url}/api/search/songs?{params}"
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            payload: dict[str, Any] = await resp.json()
        if not payload.get("success"):
            return []
        return payload.get("data", {}).get("results", []) or []

    def track_from_song(self, song: dict[str, Any]) -> Track | None:
        stream_url = self._pick_best_url(song.get("downloadUrl") or [])
        if not stream_url:
            return None

        artists = song.get("artists", {}).get("primary") or []
        artist_name = artists[0].get("name", "Unknown Artist") if artists else "Unknown Artist"

        return Track(
            title=html.unescape(song.get("name", "Unknown Title")),
            stream_url=stream_url,
            page_url=song.get("url", ""),
            artist=html.unescape(artist_name),
            duration=int(song.get("duration") or 0),
            image_url=self._pick_best_image(song.get("image") or []),
        )

    async def search_similar_track(
        self,
        session,
        seed_track: Track,
        exclude_keys: set[str] | None = None,
    ) -> Track | None:
        base_query = f"{seed_track.title} {seed_track.artist}".strip()
        candidates = await self.search_tracks_raw(session, base_query, limit=20)

        if not candidates:
            candidates = await self.search_tracks_raw(session, seed_track.artist, limit=20)

        if not candidates:
            return None

        seed_title = self._normalize_text(seed_track.title)
        seed_artist = self._normalize_text(seed_track.artist)
        seed_url = (seed_track.page_url or "").strip()

        filtered: list[dict[str, Any]] = []
        for song in candidates:
            name = self._normalize_text(str(song.get("name", "")))
            primary = song.get("artists", {}).get("primary") or []
            artist = self._normalize_text(primary[0].get("name", "")) if primary else ""
            page_url = str(song.get("url", "")).strip()

            if seed_url and page_url == seed_url:
                continue
            if name == seed_title and artist == seed_artist:
                continue
            if exclude_keys and f"{name}|{artist}" in exclude_keys:
                continue
            filtered.append(song)

        if not filtered:
            return None

        picked = self._select_best_song(filtered, base_query)
        if not picked:
            return None

        stream_url = self._pick_best_url(picked.get("downloadUrl") or [])
        if not stream_url:
            return None

        artists = picked.get("artists", {}).get("primary") or []
        artist_name = artists[0].get("name", "Unknown Artist") if artists else "Unknown Artist"

        return Track(
            title=html.unescape(picked.get("name", "Unknown Title")),
            stream_url=stream_url,
            page_url=picked.get("url", ""),
            artist=html.unescape(artist_name),
            duration=int(picked.get("duration") or 0),
            image_url=self._pick_best_image(picked.get("image") or []),
        )

    @staticmethod
    def _pick_best_url(download_urls: list[dict[str, str]]) -> str | None:
        if not download_urls:
            return None

        def quality_value(item: dict[str, str]) -> int:
            quality = item.get("quality", "")
            digits = "".join(ch for ch in quality if ch.isdigit())
            return int(digits) if digits else 0

        best = max(download_urls, key=quality_value)
        return best.get("url")

    @staticmethod
    def _normalize_text(text: str) -> str:
        return "".join(ch.lower() for ch in text if ch.isalnum() or ch.isspace()).strip()

    def _select_best_song(self, songs: list[dict[str, Any]], query: str) -> dict[str, Any] | None:
        if not songs:
            return None

        def play_count(song: dict[str, Any]) -> int:
            play_count = song.get("playCount")
            if isinstance(play_count, str) and play_count.isdigit():
                play_count = int(play_count)
            if not isinstance(play_count, int):
                play_count = 0
            return play_count

        return max(songs, key=play_count)

    @staticmethod
    def _pick_best_image(images: list[dict[str, str]]) -> str | None:
        if not images:
            return None

        def quality_value(item: dict[str, str]) -> int:
            quality = item.get("quality", "")
            digits = "".join(ch for ch in quality if ch.isdigit())
            return int(digits) if digits else 0

        best = max(images, key=quality_value)
        return best.get("url")
