"""Chat completion against a local Ollama server (single connection pool, no urllib retry storms)."""

from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

MODEL_PRESETS: tuple[str, ...] = (
    "gpt-oss",
    "gpt-oss:20b",
    "gpt-oss:120b",
    "llama3.2",
    "llama3.1",
    "mistral",
    "qwen2.5",
    "phi3",
    "gemma2",
)

CONNECT_TIMEOUT_S = 90.0
READ_TIMEOUT_S = 600.0
LIST_TIMEOUT_S = (45.0, 45.0)
PING_TIMEOUT_S = (5.0, 10.0)
CHAT_RETRIES = 5
CHAT_RETRY_BACKOFF_S = 2.0
LIST_RETRIES = 3
LIST_RETRY_BACKOFF_S = 1.5


def normalize_ollama_base(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return DEFAULT_OLLAMA_HOST.rstrip("/")
    if not u.startswith(("http://", "https://")):
        u = "http://" + u.lstrip("/")
    return u.rstrip("/")


def merge_model_choices(discovered: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in MODEL_PRESETS:
        if m not in seen:
            seen.add(m)
            out.append(m)
    for m in sorted(discovered):
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _session() -> requests.Session:
    """One urllib attempt per call; keep-alive reduces reconnect churn."""
    s = requests.Session()
    adapter = HTTPAdapter(
        pool_connections=1,
        pool_maxsize=2,
        max_retries=Retry(total=0, redirect=0),
    )
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"Connection": "keep-alive"})
    return s


_SESSION = _session()


def _request_with_retries(
    method: str,
    url: str,
    *,
    json_body: dict[str, Any] | None = None,
    timeout: float | tuple[float, float],
    retries: int,
    backoff_s: float,
    err_context: str,
) -> requests.Response:
    if retries < 1:
        retries = 1
    for attempt in range(retries):
        try:
            if method.upper() == "POST":
                return _SESSION.post(url, json=json_body, timeout=timeout)
            return _SESSION.get(url, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < retries - 1:
                time.sleep(backoff_s)
                continue
            raise RuntimeError(
                f"{err_context} After {retries} attempts: {e!s}. "
                "Keep the Ollama app running, check the URL (e.g. http://127.0.0.1:11434), "
                "and avoid starting a second heavy job until the queue finishes."
            ) from e


def ollama_ping(base_url: str = DEFAULT_OLLAMA_HOST) -> bool:
    """Fast check: GET /api/tags returns 200."""
    base = normalize_ollama_base(base_url)
    url = urljoin(base + "/", "api/tags")
    try:
        r = _SESSION.get(url, timeout=PING_TIMEOUT_S)
        return r.status_code == 200
    except requests.RequestException:
        return False


def ollama_chat(
    messages: list[dict[str, str]],
    *,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_OLLAMA_HOST,
    format_json: bool = False,
) -> str:
    base = normalize_ollama_base(base_url)
    url = urljoin(base + "/", "api/chat")
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if format_json:
        payload["format"] = "json"

    r = _request_with_retries(
        "POST",
        url,
        json_body=payload,
        timeout=(CONNECT_TIMEOUT_S, READ_TIMEOUT_S),
        retries=CHAT_RETRIES,
        backoff_s=CHAT_RETRY_BACKOFF_S,
        err_context=f"Could not reach Ollama at {base}.",
    )

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


def ollama_list_models(base_url: str = DEFAULT_OLLAMA_HOST) -> list[str]:
    base = normalize_ollama_base(base_url)
    url = urljoin(base + "/", "api/tags")
    try:
        r = _request_with_retries(
            "GET",
            url,
            json_body=None,
            timeout=LIST_TIMEOUT_S,
            retries=LIST_RETRIES,
            backoff_s=LIST_RETRY_BACKOFF_S,
            err_context=f"Could not list models at {base}.",
        )
        if r.status_code != 200:
            return []
        data = r.json()
        out: list[str] = []
        for m in data.get("models") or []:
            name = m.get("name")
            if isinstance(name, str) and name:
                out.append(name)
        return sorted(set(out))
    except Exception:
        return []
