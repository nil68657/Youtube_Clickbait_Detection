@echo off
REM Build a single-file Windows .exe (requires: uv sync --group dev)
cd /d "%~dp0.."
uv sync --group dev
uv run pyinstaller --noconfirm --clean ^
  --onefile --windowed ^
  --name youtube-clickbait ^
  --collect-all yt_dlp ^
  --collect-submodules youtube_clickbait ^
  --hidden-import youtube_transcript_api ^
  youtube_clickbait\tk_app.py
echo.
echo Output: dist\youtube-clickbait.exe
pause
