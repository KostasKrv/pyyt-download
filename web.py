"""Web interface: type a video ID, press Download, the mp4 lands in SAVE_PATH."""
import itertools
import os
import queue
import threading

from flask import Flask, abort, jsonify, request, send_from_directory

from download import SAVE_PATH, download, parse_video_id

app = Flask(__name__)

jobs = {}  # job id -> dict(video_id, status, percent, file, error)
jobs_lock = threading.Lock()
job_queue = queue.Queue()
job_ids = itertools.count(1)


def update(job_id, **fields):
    with jobs_lock:
        jobs[job_id].update(fields)


def worker():
    # one download at a time; the rest wait in the queue
    while True:
        job_id = job_queue.get()
        parts_done = 0

        def hook(d):
            nonlocal parts_done
            if "postprocessor" in d:
                if d["status"] == "started" and d["postprocessor"] == "Merger":
                    update(job_id, status="merging")
            elif d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                if total:
                    # video and audio are separate parts, show them as one bar
                    pct = (parts_done + d["downloaded_bytes"] / total) * 50
                    update(job_id, status="downloading", percent=min(pct, 99))
            elif d["status"] == "finished":
                parts_done = min(parts_done + 1, 1)

        try:
            path = download(jobs[job_id]["video_id"], progress_hook=hook, quiet=True)
            update(job_id, status="done", percent=100, file=os.path.basename(path))
        except Exception as e:  # yt-dlp errors are shown to the user as they are
            update(job_id, status="error", error=str(e).removeprefix("ERROR: "))
        finally:
            job_queue.task_done()


@app.get("/")
def index():
    return PAGE


@app.post("/api/download")
def start_download():
    video_id = parse_video_id((request.get_json(silent=True) or {}).get("id", ""))
    if not video_id:
        return jsonify(error="Invalid video ID or link"), 400
    job_id = next(job_ids)
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "video_id": video_id, "status": "queued", "percent": 0}
    job_queue.put(job_id)
    return jsonify(jobs[job_id])


@app.get("/api/jobs")
def list_jobs():
    with jobs_lock:
        return jsonify(sorted(jobs.values(), key=lambda j: -j["id"]))


@app.get("/api/files")
def list_files():
    os.makedirs(SAVE_PATH, exist_ok=True)
    files = [f for f in os.listdir(SAVE_PATH) if f.endswith(".mp4")]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(SAVE_PATH, f)), reverse=True)
    return jsonify(files)


@app.get("/files/<path:name>")
def get_file(name):
    if not name.endswith(".mp4"):
        abort(404)
    return send_from_directory(SAVE_PATH, name, as_attachment=True)


def serve(port=8080):
    threading.Thread(target=worker, daemon=True).start()
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"Web interface on http://localhost:{port} (saving to {SAVE_PATH})")
    app.run(host=host, port=port)


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pyyt-download</title>
<style>
  :root { --bg: #f6f7f9; --card: #fff; --text: #1d2330; --muted: #667085; --line: #e3e6eb;
          --accent: #2f6fdf; --ok: #1f8a4c; --err: #c0362c; }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #14171c; --card: #1c2027; --text: #e6e9ef; --muted: #98a2b3; --line: #2c323c;
            --accent: #5b8ff0; --ok: #43b474; --err: #ef6a5f; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text);
         font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
  main { max-width: 640px; margin: 48px auto; padding: 0 16px; }
  h1 { font-size: 1.4rem; margin: 0 0 4px; }
  p.sub { color: var(--muted); margin: 0 0 24px; }
  form { display: flex; gap: 8px; }
  input { flex: 1; min-width: 0; padding: 10px 12px; font: inherit; color: var(--text);
          background: var(--card); border: 1px solid var(--line); border-radius: 8px; }
  button { padding: 10px 18px; font: inherit; font-weight: 600; color: #fff; background: var(--accent);
           border: 0; border-radius: 8px; cursor: pointer; }
  #msg { color: var(--err); min-height: 1.5em; margin: 6px 0 16px; font-size: .9rem; }
  h2 { font-size: 1rem; margin: 24px 0 8px; }
  ul { list-style: none; padding: 0; margin: 0; }
  li { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px;
       margin-bottom: 8px; overflow-wrap: anywhere; }
  .row { display: flex; justify-content: space-between; gap: 12px; font-size: .9rem; }
  .status { color: var(--muted); white-space: nowrap; }
  .done { color: var(--ok); } .error { color: var(--err); }
  .bar { height: 6px; background: var(--line); border-radius: 3px; margin-top: 8px; overflow: hidden; }
  .bar div { height: 100%; background: var(--accent); transition: width .3s; }
  a { color: var(--accent); }
  .empty { color: var(--muted); font-size: .9rem; }
</style>
</head>
<body>
<main>
  <h1>pyyt-download</h1>
  <p class="sub">Only download videos you own or have permission to download.</p>
  <form id="form">
    <input id="id" placeholder="Video ID or link, e.g. jNQXAC9IVRw" autocomplete="off" autofocus>
    <button>Download</button>
  </form>
  <div id="msg"></div>
  <h2>Downloads</h2>
  <ul id="jobs"></ul>
  <h2>Files</h2>
  <ul id="files"></ul>
</main>
<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fileLink = (f) => `<a href="/files/${encodeURIComponent(f)}">${esc(f)}</a>`;
let timer;
const LABELS = { queued: "waiting", downloading: "downloading", merging: "merging", done: "done", error: "failed" };

$("#form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("#msg").textContent = "";
  const res = await fetch("/api/download", { method: "POST", headers: { "Content-Type": "application/json" },
                                             body: JSON.stringify({ id: $("#id").value }) });
  if (!res.ok) { $("#msg").textContent = (await res.json()).error; return; }
  $("#id").value = "";
  refresh();
});

async function refresh() {
  clearTimeout(timer);
  const [jobs, files] = await Promise.all([fetch("/api/jobs").then((r) => r.json()),
                                           fetch("/api/files").then((r) => r.json())]);
  $("#jobs").innerHTML = jobs.length ? jobs.map((j) => `
    <li><div class="row">
      <span>${j.file ? fileLink(j.file) : esc(j.video_id)}</span>
      <span class="status ${j.status}">${LABELS[j.status]}${j.status === "downloading" ? " " + Math.round(j.percent) + "%" : ""}</span>
    </div>
    ${j.error ? `<div class="error">${esc(j.error)}</div>` : ""}
    ${["queued", "downloading", "merging"].includes(j.status) ? `<div class="bar"><div style="width:${j.percent}%"></div></div>` : ""}
    </li>`).join("") : '<li class="empty">Nothing yet.</li>';
  $("#files").innerHTML = files.length ? files.map((f) => `<li>${fileLink(f)}</li>`).join("")
                                       : '<li class="empty">No files in the downloads folder.</li>';
  const busy = jobs.some((j) => ["queued", "downloading", "merging"].includes(j.status));
  timer = setTimeout(refresh, busy ? 1000 : 5000);
}
refresh();
</script>
</body>
</html>
"""
