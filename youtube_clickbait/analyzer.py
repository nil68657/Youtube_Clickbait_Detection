"""Use a local LLM to summarize transcript and compare it to the title."""

from __future__ import annotations

import json
import re
from typing import Any

from youtube_clickbait.ollama_client import DEFAULT_MODEL, ollama_chat

SYSTEM = """You are a careful analyst of YouTube videos. You only use the transcript text \
provided (not general knowledge). Be concise and honest when the transcript is vague or \
off-topic compared to the title.

You must respond with a single JSON object (no markdown fences) using exactly these keys:
- "summary": string, 2-5 sentences describing what the video actually covers according to the transcript.
- "verdict": one of "match", "partial", "clickbait"
  - "match": the main content clearly delivers what the title promises.
  - "partial": some overlap, but the title exaggerates, omits context, or highlights a minor part.
  - "clickbait": the substance does not reasonably support the title's main claim or emotional hook.
- "confidence": number from 0.0 to 1.0 (your confidence in this verdict).
- "reasoning": string, 2-4 sentences explaining the verdict with reference to title vs transcript.
"""


def build_user_message(title: str, transcript_excerpt: str) -> str:
    return (
        f"Video title:\n{title}\n\n"
        f"Transcript (may be truncated):\n{transcript_excerpt}\n\n"
        "Analyze title vs transcript and output the JSON object as specified."
    )


def _parse_json_loose(text: str) -> dict[str, Any]:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if m:
        text = m.group(0)
    return json.loads(text)


def analyze_title_vs_transcript(
    title: str,
    transcript: str,
    *,
    model: str = DEFAULT_MODEL,
    ollama_host: str,
) -> dict[str, Any]:
    """
    Returns a dict with keys: summary, verdict, confidence, reasoning (and raw_model_output on fallback).
    """
    user = build_user_message(title, transcript)
    raw = ollama_chat(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        model=model,
        base_url=ollama_host,
        format_json=True,
    )

    try:
        data = _parse_json_loose(raw)
    except json.JSONDecodeError:
        return {
            "summary": raw[:2000],
            "verdict": "partial",
            "confidence": 0.2,
            "reasoning": "The model did not return valid JSON; showing raw output in summary.",
            "raw_model_output": raw,
        }

    verdict = str(data.get("verdict", "partial")).lower().strip()
    if verdict not in ("match", "partial", "clickbait"):
        verdict = "partial"

    conf = data.get("confidence", 0.5)
    try:
        confidence = float(conf)
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    return {
        "summary": str(data.get("summary", "")).strip() or "(no summary)",
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": str(data.get("reasoning", "")).strip() or "(no reasoning)",
    }
