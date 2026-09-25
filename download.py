"""Download a YouTube video as mp4.

Usage:
    python download.py [ID or link]     download one video (asks for the ID if omitted)
    python download.py serve [PORT]     start the web interface (default port 8080)
"""
import os
import re
import sys

import yt_dlp

HERE = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.environ.get("DOWNLOAD_DIR", os.path.join(HERE, "downloads"))

ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
URL_RE = re.compile(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})")

# deno and ffmpeg from bin/ when installed by setup.sh (in Docker they are already on PATH)
os.environ["PATH"] = os.path.join(HERE, "bin") + os.pathsep + os.environ["PATH"]


def parse_video_id(text):
    text = text.strip()
    if ID_RE.match(text):
        return text
    m = URL_RE.search(text)
    return m.group(1) if m else None


def download(video_id, progress_hook=None, quiet=False):
    """Download the video into SAVE_PATH and return the path of the mp4 file."""
    os.makedirs(SAVE_PATH, exist_ok=True)
    ydl_opts = {
        # best quality as mp4 (video + audio merged with ffmpeg)
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(SAVE_PATH, "%(title)s [%(id)s].%(ext)s"),
        "quiet": quiet,
        "noprogress": quiet,
    }
    if progress_hook:
        ydl_opts["progress_hooks"] = [progress_hook]
        ydl_opts["postprocessor_hooks"] = [progress_hook]
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
        downloads = info.get("requested_downloads") or [{}]
        return downloads[0].get("filepath") or ydl.prepare_filename(info).rsplit(".", 1)[0] + ".mp4"


def main():
    args = sys.argv[1:]
    if args and args[0] == "serve":
        from web import serve
        serve(int(args[1]) if len(args) > 1 else 8080)
        return

    video_id = parse_video_id(args[0]) if args else None
    if args and video_id is None:
        sys.exit(f"Invalid video ID or link: {args[0]}")
    while video_id is None:
        video_id = parse_video_id(input("Video ID or link: "))
        if video_id is None:
            print("Invalid ID, try again.")

    print("Saved:", download(video_id))


if __name__ == "__main__":
    main()
