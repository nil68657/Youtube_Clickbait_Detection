"""
Start `ollama serve` when the app launches if nothing is listening yet.
Only the child process we start is stopped when the app exits.
"""

from __future__ import annotations

import atexit
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from youtube_clickbait.ollama_client import DEFAULT_OLLAMA_HOST, normalize_ollama_base, probe_ollama

STARTUP_TIMEOUT_S = 120.0


def find_ollama_executable() -> Optional[str]:
    """
    Resolve path to the Ollama CLI. Windows often installs without PATH for GUI apps.

    Order: OLLAMA_EXE env, PATH (ollama / ollama.exe), then common install locations.
    """
    env = os.environ.get("OLLAMA_EXE", "").strip()
    if env and Path(env).is_file():
        return str(Path(env).resolve())

    for name in ("ollama", "ollama.exe"):
        w = shutil.which(name)
        if w and Path(w).is_file():
            return str(Path(w).resolve())

    candidates: list[Path] = []

    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            candidates.append(Path(local) / "Programs" / "Ollama" / "ollama.exe")
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        candidates.append(Path(pf) / "Ollama" / "ollama.exe")
        pfx86 = os.environ.get("ProgramFiles(x86)", "")
        if pfx86:
            candidates.append(Path(pfx86) / "Ollama" / "ollama.exe")
    elif sys.platform == "darwin":
        candidates.extend(
            [
                Path("/usr/local/bin/ollama"),
                Path("/opt/homebrew/bin/ollama"),
            ]
        )
    else:
        candidates.extend(
            [
                Path("/usr/local/bin/ollama"),
                Path("/usr/bin/ollama"),
            ]
        )

    for p in candidates:
        if p.is_file():
            return str(p.resolve())

    return None

_child_we_started: Optional[subprocess.Popen] = None


def cleanup_ollama_child() -> None:
    """Terminate Ollama only if this app started it."""
    global _child_we_started
    proc = _child_we_started
    _child_we_started = None
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


atexit.register(cleanup_ollama_child)


def ensure_ollama_running(base_url: str | None = None) -> tuple[bool, str, Optional[subprocess.Popen]]:
    """
    If Ollama already responds, return (True, message, None).
    Otherwise try to run `ollama serve` and wait until /api/tags works.

    Set OLLAMA_AUTO_START=0 to skip starting a child (only probe).
    """
    global _child_we_started

    base = normalize_ollama_base(base_url or DEFAULT_OLLAMA_HOST)
    auto = os.environ.get("OLLAMA_AUTO_START", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )

    ok, _working, _msg = probe_ollama(base)
    if ok:
        return True, "Ollama is already running.", None

    if not auto:
        return (
            False,
            "Ollama is not running (OLLAMA_AUTO_START=0 — start it manually or unset).",
            None,
        )

    exe = find_ollama_executable()
    if not exe:
        return (
            False,
            "Could not find ollama.exe. Install from https://ollama.com, "
            "or set OLLAMA_EXE to the full path (e.g. "
            r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe on Windows).",
            None,
        )

    kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.PIPE,
        "stdin": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        cnw = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if cnw:
            kwargs["creationflags"] = cnw

    try:
        proc = subprocess.Popen([exe, "serve"], **kwargs)
    except OSError as e:
        return False, f"Could not start `ollama serve`: {e}", None

    deadline = time.time() + STARTUP_TIMEOUT_S
    while time.time() < deadline:
        if probe_ollama(base)[0]:
            _child_we_started = proc
            return True, "Started Ollama (`ollama serve`) for this session.", proc
        if proc.poll() is not None:
            err = ""
            if proc.stderr:
                err = proc.stderr.read().decode(errors="replace")[:800]
            return (
                False,
                f"`ollama serve` exited (code {proc.returncode}). {err}",
                None,
            )
        time.sleep(0.35)

    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
    return (
        False,
        "Timed out waiting for Ollama to listen. Is port 11434 in use? Try starting Ollama manually.",
        None,
    )
