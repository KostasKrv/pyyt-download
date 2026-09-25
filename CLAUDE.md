# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Downloads a YouTube video as mp4 with `yt-dlp`, given a video ID or link. It runs locally (WSL or x86_64 Linux) or in Docker, as a CLI or a web interface. There is no build system, test suite or linter.

- `download.py`: the core `download(video_id, progress_hook)` plus the CLI. It takes an ID or link as an argument (or asks for one with `input()`); `download.py serve [PORT]` starts the web interface. It saves to `$DOWNLOAD_DIR`, by default `downloads/`.
- `web.py`: the Flask web interface, with the HTML/JS inline in `PAGE`. A single worker thread takes jobs from a queue, so downloads run one at a time. Jobs are kept in memory, and their progress comes from yt-dlp progress and postprocessor hooks. Video and audio each count as half of the progress bar. `/files/<name>` serves only `.mp4` files from `SAVE_PATH`. It binds to `$HOST`, which defaults to `127.0.0.1`.
- `Dockerfile` / `docker-compose.yml`: `python:3.12-slim` plus apt `ffmpeg`, with deno copied from `denoland/deno:bin`. The entrypoint is `download.py` and the default CMD is `serve`. `/downloads` is the shared volume. Compose runs as `${UID}:${GID}`, so `HOME`, `XDG_CACHE_HOME` and `DENO_DIR` point to `/tmp` to stay writable. It publishes the port on `127.0.0.1` only.
- `setup.sh`: one-time local setup, all inside this folder.
  - Installs `uv` if it's missing, then makes a Python 3.12 venv in `.venv/`. Older system Pythons, such as 3.8, only get outdated yt-dlp releases that fail against YouTube.
  - Installs `yt-dlp[default]` (the extra brings `yt-dlp-ejs`), `imageio-ffmpeg` and `flask`.
  - Downloads **deno** into `bin/` and symlinks the imageio ffmpeg binary as `bin/ffmpeg`.

`.venv/`, `bin/` and `downloads/` are generated and gitignored.

## Commands

```bash
./setup.sh                                  # first time, and to upgrade yt-dlp/deno when YouTube breaks things
.venv/bin/python download.py jNQXAC9IVRw    # or a full link, or no argument to be prompted
.venv/bin/python download.py serve          # web interface on http://localhost:8080

docker compose build
docker compose run --rm pyyt jNQXAC9IVRw   # CLI in Docker
docker compose up -d                        # web interface in Docker
```

## How it works / gotchas

- `download.py` puts `bin/` at the front of `PATH` at runtime, so yt-dlp finds `deno` and `ffmpeg`. yt-dlp looks for an executable named exactly `ffmpeg`, which is why `setup.sh` makes the symlink.
- yt-dlp needs a JS runtime (deno) plus the EJS solver scripts to solve YouTube's signature and n challenges. If either is missing, it only gets the thumbnail and subtitles and fails with the misleading `This video is not available`. JDownloader showing only `.jpg`/`.srt` is the same symptom. If the `yt-dlp-ejs` package isn't picked up, the option `remote_components: ["ejs:github"]` fetches the scripts instead.
- Format string: `bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b`, merged to mp4.
- `parse_video_id` accepts an 11-character ID or a `watch?v=`, `youtu.be/`, `shorts/`, `embed/` or `live/` URL.
- To test without a full download, pass `download_ranges=yt_dlp.utils.download_range_func(None, [(0, 20)])` in the options.
- Don't use pytube: it no longer works against YouTube and fails with `HTTP Error 400` on the InnerTube `player` call.

## Policy constraints (owner requirement)

The owner doesn't want anything that risks their Google account or breaks Google/YouTube policies. When YouTube blocks a download (e.g. `HTTP Error 403: Forbidden` from cloud or Colab IPs), do **not** work around it. That means no player-client rotation, no cookies or account sign-in, and no proxies. YouTube's ToS forbids downloading except through YouTube's own features or with permission from YouTube and the rights holder, and the README tells users to download only videos they own or have permission for.
