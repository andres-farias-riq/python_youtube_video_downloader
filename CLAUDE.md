# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

Install dependencies into a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

## Architecture

This is a small Python CLI app (~140 lines across 3 source files):

- **`main.py`** — All application logic: CLI menus, video/audio download flows using `yt-dlp`. Audio-to-MP3 conversion and video+audio merging are handled by `yt-dlp` via ffmpeg internally.
- **`config.py`** — Single constant `RUTA_DESCARGAS`, the filesystem path where downloads are saved. Change this to point to your local downloads folder.
- **`conf_management.py`** — Thin wrapper that exposes `get_ruta_descargas()` from `config.py`.

### Download modes (selected interactively at runtime)

1. **Quick video+audio** — Best H.264 MP4 video up to 720p plus best M4A audio, merged via ffmpeg (YouTube no longer serves bundled video+audio streams). Saved to `<RUTA_DESCARGAS>/video/`.
2. **Video with quality selection** — Lists available resolutions; downloads the selected video stream and best audio, then merges them via ffmpeg into a single MP4. Saved to `<RUTA_DESCARGAS>/video/`.
3. **Audio only** — Downloads best audio stream and converts to MP3 at 192kbps via ffmpeg. Saved to `<RUTA_DESCARGAS>/audio/`.

Input can be a single URL or a plain-text file containing one URL per line (batch mode). In batch mode, quality selection defaults to the first (highest-resolution) stream.

Input can be a single URL or a plain-text file containing one URL per line (batch mode). In batch mode, quality selection defaults to the highest-resolution stream.

**Note:** all modes require `ffmpeg` installed on the system (`brew install ffmpeg` on Mac).
