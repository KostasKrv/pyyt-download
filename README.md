# pyyt-download

Downloads a YouTube video as mp4 (best available quality, video and audio merged) with [yt-dlp](https://github.com/yt-dlp/yt-dlp). It runs as a command or as a small web interface, either locally or in Docker.

> Only download videos that you own or have the owner's permission to download. [YouTube's Terms of Service](https://www.youtube.com/static?template=terms) don't allow downloading with third-party tools. For videos on your own channel, the official way is YouTube Studio → Content → ⋮ → **Download**.

## Requirements

- **Windows 10/11 with WSL (Ubuntu)**, or any x86_64 Linux.
  - If you don't have WSL: open PowerShell as administrator, run `wsl --install`, restart, and open "Ubuntu" from the Start menu.
- An internet connection. `setup.sh` installs everything else (Python 3.12, yt-dlp, deno, ffmpeg).

## Setup (once)

Clone the repository, e.g. into `C:\workdir`, then run in the WSL terminal:

```bash
cd /mnt/c/workdir
git clone https://github.com/KostasKrv/pyyt-download.git
cd pyyt-download
./setup.sh
```

At the end it prints the yt-dlp and deno versions. If you get `Permission denied`, first run `chmod +x setup.sh`.

## Usage

```bash
.venv/bin/python download.py
```

Type the video ID and press Enter. The ID is the part after `v=` in the link: for `https://www.youtube.com/watch?v=jNQXAC9IVRw` it's `jNQXAC9IVRw`. A full link also works (`watch?v=`, `youtu.be/`, `shorts/`).

You can also pass the ID directly:

```bash
.venv/bin/python download.py jNQXAC9IVRw
```

The file is saved in the `downloads/` folder as `Title [ID].mp4`. From Windows it's in `C:\workdir\pyyt-download\downloads`.

### Web interface

```bash
.venv/bin/python download.py serve
```

Open http://localhost:8080, type the video ID or link and press **Download**. The page shows progress and lists the files in `downloads/`, which you can also download from the browser.

## Docker

Requires Docker (on Windows: Docker Desktop). The container writes into `downloads/` in this folder, which is shared with it.

Build once:

```bash
docker compose build
```

As a command:

```bash
docker compose run --rm pyyt jNQXAC9IVRw    # or with no ID to be asked for one
```

As a web interface on http://localhost:8080:

```bash
docker compose up -d      # stop with: docker compose down
```

The web interface is only reachable from this computer. To open it to your network, change `127.0.0.1:8080:8080` to `8080:8080` in `docker-compose.yml`. It has no login, so only do that on a network you trust.

Without compose:

```bash
docker build -t pyyt-download .
docker run --rm -v "$PWD/downloads:/downloads" --user "$(id -u):$(id -g)" pyyt-download jNQXAC9IVRw
docker run -d -p 127.0.0.1:8080:8080 -v "$PWD/downloads:/downloads" --user "$(id -u):$(id -g)" pyyt-download
```

To update yt-dlp in Docker, rebuild without cache: `docker compose build --no-cache`.

## If it stops working

YouTube changes often, and yt-dlp then needs an update. If you get `This video is not available` for a video that plays fine in the browser, or only a thumbnail and subtitles are downloaded, run again:

```bash
./setup.sh
```

This installs the latest yt-dlp and deno.
