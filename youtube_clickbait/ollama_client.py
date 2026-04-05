"""Chat completion against a local Ollama server."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urljoin

import requests

DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")


def ollama_chat(
    messages: list[dict[str, str]],
    *,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_OLLAMA_HOST,
    format_json: bool = False,
    timeout_s: float = 600.0,
) -> str:
    """
    POST /api/chat and return assistant message content.
    Raises RuntimeError on HTTP errors or missing content.
    """
    url = urljoin(base_url.rstrip("/") + "/", "api/chat")
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if format_json:
        payload["format"] = "json"

    try:
        r = requests.post(url, json=payload, timeout=timeout_s)
    except requests.RequestException as e:
        raise RuntimeError(
            f"Could not reach Ollama at {base_url}. Is `ollama serve` running? ({e})"
        ) from e

    if r.status_code != 200:
        try:
            detail = r.json()
        except Exception:
            detail = r.text[:500]
        raise RuntimeError(f"Ollama error ({r.status_code}): {detail}")

    data = r.json()
    msg = data.get("message") or {}
    content = msg.get("content")
    if not content:
        raise RuntimeError(f"Unexpected Ollama response: {json.dumps(data)[:800]}")
    return content.strip()


def ollama_list_models(base_url: str = DEFAULT_OLLAMA_HOST, timeout_s: float = 10.0) -> list[str]:
    """Return model names from GET /api/tags, or empty list on failure."""
    url = urljoin(base_url.rstrip("/") + "/", "api/tags")
    try:
        r = requests.get(url, timeout=timeout_s)
        if r.status_code != 200:
            return []
        data = r.json()
        out: list[str] = []
        for m in data.get("models") or []:
            name = m.get("name")
            if isinstance(name, str) and name:
                out.append(name)
        return sorted(set(out))
    except requests.RequestException:
        return []
