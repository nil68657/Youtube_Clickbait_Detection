# YouTube clickbait detection

Desktop app (**Tkinter** + **Ollama**) that reads a video’s **captions**, summarizes them, and compares that summary to the **title**. There is **no browser** and **no local web server** — only a normal window.

## Prerequisites

1. Install [Ollama](https://ollama.com) so the `ollama` command is on your PATH (default API `http://127.0.0.1:11434`). When you run the app, it tries to start **`ollama serve`** automatically if nothing is already listening; closing the app stops only that child process (if the app started it).
2. Pull at least one model, for example: `ollama pull llama3.2` or `ollama pull gpt-oss:20b` ([GPT-OSS on Ollama](https://ollama.com/library/gpt-oss)).
3. Install [uv](https://docs.astral.sh/uv/).

The window shows **Ollama status** (reachable or not) and refreshes every ~12 seconds. Analysis jobs go through a **FIFO queue**: only **one** Ollama generation runs at a time; the next job starts when the current response is finished. This avoids overlapping requests that often trigger “max retries exceeded” / connection errors.

### If Ollama shows “not reachable”

1. **Start Ollama** (desktop app or `ollama serve`). In a terminal, `ollama list` must work.
2. In the app, set **Ollama URL** to `http://127.0.0.1:11434` or `http://localhost:11434` and click **Test connection**. If one works, the dialog can suggest switching the URL.
3. **HTTP_PROXY / corporate proxy**: this project uses `requests` with **proxy env vars ignored** for Ollama so `localhost` is not sent through a proxy. If it still fails, check VPN/firewall and that **port 11434** is allowed for local traffic on Windows.

## Setup

```bash
uv sync
```

## Run the desktop UI

```bash
uv run youtube-clickbait
```

Or:

```bash
uv run python app.py
```

Paste a YouTube URL and click **Analyze (add to queue)**. You can queue several URLs; they run in order.

Videos **without captions** cannot be analyzed (this project does not download or transcribe audio).

### Environment (optional)

| Variable       | Meaning                 | Default              |
|----------------|-------------------------|----------------------|
| `OLLAMA_HOST`  | Ollama base URL         | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Default model in the UI | `llama3.2`           |
| `OLLAMA_AUTO_START` | Set to `0` to disable auto `ollama serve` | `1` (enabled) |
| `OLLAMA_EXE` | Full path to `ollama` / `ollama.exe` if not on PATH | (unset) |

If the app says **ollama was not found** but Ollama is installed, Windows often puts the binary at `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`. Either add that folder to your user PATH, or set `OLLAMA_EXE` to that file once (PowerShell: `$env:OLLAMA_EXE = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"`).

## Build a Windows `.exe`

From the repo root (installs dev deps including PyInstaller):

```bash
uv sync --group dev
scripts\build_exe.bat
```

The executable is written to `dist\youtube-clickbait.exe`. Copy that file anywhere; Ollama must still be installed and running on the machine.

## iOS

There is **no iOS app** in this repository. Python + Tkinter + Ollama’s local API do not map to an App Store–friendly stack. A real iOS client would be a separate native app (Swift/SwiftUI) that calls Ollama on your Mac or over the network.

Add packages with `uv add <package>`.
