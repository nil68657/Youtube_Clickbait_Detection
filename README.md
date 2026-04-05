# YouTube clickbait detection

Desktop app (**Tkinter** + **Ollama**) that reads a video’s **captions**, summarizes them, and compares that summary to the **title**. There is **no browser** and **no local web server** — only a normal window.

## Prerequisites

1. Install [Ollama](https://ollama.com) and keep it running (default `http://127.0.0.1:11434`).
2. Pull a model, for example: `ollama pull llama3.2`
3. Install [uv](https://docs.astral.sh/uv/).

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

Paste a YouTube URL and click **Analyze**.

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
