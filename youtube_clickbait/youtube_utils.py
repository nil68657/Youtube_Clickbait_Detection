"""Fetch YouTube title and transcript text."""

from __future__ import annotations

import re
from typing import Optional

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeRequestFailed,
)


def extract_video_id(url: str) -> Optional[str]:
    """Return 11‑char video id if *url* looks like a YouTube watch or embed URL."""
    if not url or not url.strip():
        return None
    s = url.strip()
    patterns = [
        r"(?:youtube\.com/watch\?v=)([0-9A-Za-z_-]{11})",
        r"(?:youtube\.com/embed/)([0-9A-Za-z_-]{11})",
        r"(?:youtu\.be/)([0-9A-Za-z_-]{11})",
        r"(?:youtube\.com/shorts/)([0-9A-Za-z_-]{11})",
        r"(?:youtube\.com/live/)([0-9A-Za-z_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, s)
        if m:
            return m.group(1)
    return None


def get_title(url: str) -> str:
    """Video title via yt-dlp (no download)."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    title = info.get("title") or ""
    if not isinstance(title, str):
        title = str(title)
    return title.strip()


def _transcript_text_for_language(video_id: str, lang_codes: list[str]) -> str:
    """Fetch transcript text, trying languages in order."""
    try:
        ytt = YouTubeTranscriptApi()
        transcript_list = ytt.list(video_id)
    except Exception as e:
        raise RuntimeError(f"Could not list transcripts: {e}") from e

    chosen = None
    for code in lang_codes:
        try:
            chosen = transcript_list.find_transcript([code])
            break
        except Exception:
            continue

    if chosen is None:
        try:
            chosen = transcript_list.find_generated_transcript(["en"])
        except Exception:
            pass

    if chosen is None:
        try:
            for t in transcript_list:
                chosen = t
                break
        except Exception:
            pass

    if chosen is None:
        raise RuntimeError("No transcript tracks available for this video.")

    try:
        fetched = chosen.fetch()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch transcript: {e}") from e

    parts: list[str] = []
    for seg in fetched:
        if isinstance(seg, dict):
            t = (seg.get("text") or "").strip()
            if t:
                parts.append(t)
        elif hasattr(seg, "text"):
            t = str(getattr(seg, "text", "")).strip()
            if t:
                parts.append(t)
    return " ".join(parts)


def get_transcript_text(video_id: str, lang_preference: str = "en") -> str:
    """
    Full transcript as a single string. Tries preferred language, then
    manual English, generated English, then any available track.
    """
    langs: list[str] = []
    for code in (lang_preference, "en"):
        if code and code not in langs:
            langs.append(code)

    try:
        return _transcript_text_for_language(video_id, langs)
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as e:
        raise RuntimeError(
            "No usable captions for this video. Try another video or one with "
            "subtitles/captions enabled."
        ) from e
    except YouTubeRequestFailed as e:
        raise RuntimeError(f"YouTube transcript request failed: {e}") from e


def clip_transcript(text: str, max_chars: int = 28000) -> str:
    """Keep beginning (and a bit of end) so long videos still fit in context."""
    if len(text) <= max_chars:
        return text
    head = int(max_chars * 0.85)
    tail = max_chars - head
    return text[:head] + "\n\n[... middle omitted for length ...]\n\n" + text[-tail:]
