# YouTube clickbait detection

Desktop app (**Tkinter** + **Ollama**) that reads a video’s **captions**, summarizes them, and compares that summary to the **title**. There is **no browser** and **no local web server** — only a normal window.

## Prerequisites

1. Install [Ollama](https://ollama.com) and keep it running (default `http://127.0.0.1:11434`).
2. Pull at least one model, for example: `ollama pull llama3.2` or `ollama pull gpt-oss:20b` ([GPT-OSS on Ollama](https://ollama.com/library/gpt-oss)).
3. Install [uv](https://docs.astral.sh/uv/).

The window shows **Ollama status** (reachable or not) and refreshes every ~12 seconds. Analysis jobs go through a **FIFO queue**: only **one** Ollama generation runs at a time; the next job starts when the current response is finished. This avoids overlapping requests that often trigger “max retries exceeded” / connection errors.

### If Ollama still cannot be reached

Keep the Ollama app open (or `ollama serve`). Use **Ollama URL** `http://127.0.0.1:11434` or `127.0.0.1:11434`. Confirm in a terminal: `ollama list`. Pick a **model** you have pulled (`ollama pull <name>`).

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
