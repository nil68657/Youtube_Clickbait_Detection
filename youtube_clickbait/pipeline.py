"""Fetch YouTube data and run the clickbait analysis (UI-agnostic)."""

from __future__ import annotations

import re

from youtube_clickbait.analyzer import analyze_title_vs_transcript
from youtube_clickbait.ollama_client import DEFAULT_MODEL, DEFAULT_OLLAMA_HOST, normalize_ollama_base
from youtube_clickbait.youtube_utils import (
    clip_transcript,
    extract_video_id,
    get_title,
    get_transcript_text,
)


def normalize_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u.lstrip("/")
    return u


def run_pipeline(
    url: str,
    ollama_host: str,
    model: str,
    caption_lang: str,
    max_transcript_chars: int,
) -> tuple[str, str]:
    """
    Returns (markdown_report, status_line).
    """
    u = normalize_url(url)
    if not u:
        return "", "Enter a YouTube URL."

    vid = extract_video_id(u)
    if not vid:
        return "", "Could not parse a video ID from that URL."

    watch = f"https://www.youtube.com/watch?v={vid}"

    try:
        title = get_title(watch)
    except Exception as e:
        return "", f"Failed to read video metadata: {e}"

    lang = (caption_lang or "en").strip() or "en"
    try:
        transcript = get_transcript_text(vid, lang_preference=lang)
    except Exception as e:
        return (
            "",
            f"{e}\n\nTip: pick another language if captions exist only in a different language.",
        )

    clipped = clip_transcript(transcript, max_chars=max_transcript_chars)

    host = normalize_ollama_base((ollama_host or DEFAULT_OLLAMA_HOST).strip() or DEFAULT_OLLAMA_HOST)
    mdl = (model or DEFAULT_MODEL).strip() or DEFAULT_MODEL

    try:
        result = analyze_title_vs_transcript(
            title,
            clipped,
            model=mdl,
            ollama_host=host,
        )
    except RuntimeError as e:
        return "", str(e)

    verdict = result["verdict"]
    label = {
        "match": "Title matches content",
        "partial": "Partially misleading",
        "clickbait": "Likely clickbait",
    }.get(verdict, verdict)

    md = f"""## {label}

**Confidence:** {result['confidence']:.0%}

### Summary
{result['summary']}

### Title vs content
**Title:** {title}

### Reasoning
{result['reasoning']}
"""
    if result.get("raw_model_output"):
        md += (
            "\n### Raw model output (parse failed)\n\n```\n"
            + str(result["raw_model_output"])[:4000]
            + "\n```\n"
        )

    status = f"OK - video {vid} - model {mdl}"
    return md, status


def markdown_to_plain(md: str) -> str:
    """Rough markdown → plain text for Tkinter."""
    if not md:
        return ""
    t = re.sub(r"^#+\s*", "", md, flags=re.MULTILINE)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"^###\s*", "\n", t, flags=re.MULTILINE)
    t = re.sub(r"```\s*", "\n", t)
    return t.strip()
