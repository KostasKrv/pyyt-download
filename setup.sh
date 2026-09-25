#!/usr/bin/env bash
# Sets up everything download.py needs, inside this folder (no Docker)
set -euo pipefail
cd "$(dirname "$0")"

UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
if [ ! -x "$UV" ]; then
    # uv: installs Python 3.12 and packages (goes into ~/.local/bin)
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
"$UV" venv -q --allow-existing -p 3.12 .venv
# yt-dlp[default] also brings the JS challenge solver scripts (yt-dlp-ejs); imageio-ffmpeg provides ffmpeg
"$UV" pip install -q --python .venv/bin/python -U "yt-dlp[default]" imageio-ffmpeg flask

# deno: JavaScript runtime that yt-dlp needs for YouTube
mkdir -p bin
curl -fsSL -o bin/deno.zip https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip
.venv/bin/python -c "import zipfile; zipfile.ZipFile('bin/deno.zip').extractall('bin')"
rm bin/deno.zip && chmod +x bin/deno

# yt-dlp looks for an executable named exactly "ffmpeg"
ln -sf "$(.venv/bin/python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" bin/ffmpeg

.venv/bin/yt-dlp --version
bin/deno --version | head -1
