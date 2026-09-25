FROM denoland/deno:bin AS deno

FROM python:3.12-slim

# ffmpeg merges video + audio; deno solves YouTube's JS challenges for yt-dlp
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY --from=deno /deno /usr/local/bin/deno

# yt-dlp[default] also brings the JS challenge solver scripts (yt-dlp-ejs)
RUN pip install --no-cache-dir -U "yt-dlp[default]" flask

WORKDIR /app
COPY download.py web.py ./

# /downloads is the shared folder; HOME and caches must be writable when run with --user
ENV DOWNLOAD_DIR=/downloads \
    HOST=0.0.0.0 \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/.cache \
    DENO_DIR=/tmp/.deno \
    PYTHONUNBUFFERED=1
VOLUME /downloads
EXPOSE 8080

ENTRYPOINT ["python", "/app/download.py"]
CMD ["serve"]
