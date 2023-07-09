import os
from datetime import datetime, timezone
from pathlib import Path

import yt_dlp
from flask import Flask, Response, request, send_file
from feedgen.feed import FeedGenerator

app = Flask(__name__)

def download_from_youtube(video_id):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "/data/%(id)s.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(["http://www.youtube.com/watch?v=" + video_id])

def manage_storage():
    MAX_STORAGE_SIZE = 10 * 1024 ** 3
    files = sorted(Path("/data").glob("*.mp3"), key=lambda x: x.stat().st_mtime)
    total_size = sum(f.stat().st_size for f in files)
    while total_size > MAX_STORAGE_SIZE and files:
        removed_file = files.pop(0)
        total_size -= removed_file.stat().st_size
        removed_file.unlink()

@app.route("/mp3/<video_id>")
def stream_mp3(video_id):
    file_path = f"/data/{video_id}.mp3"
    if not os.path.isfile(file_path):
        download_from_youtube(video_id)
    return send_file(file_path, mimetype="audio/mpeg")

@app.route("/feed/<channel_id>")
def feed(channel_id):
    youtube_url = f"https://www.youtube.com/{channel_id}"

    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg.id(f"yt:{channel_id}")
    fg.title(channel_id)
    fg.link(href=youtube_url)

    ydl_opts = {
        "extract_flat": "in_playlist",
        "extractor_args": {"youtubetab": "approximate_date"},
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"{youtube_url}/videos", download=False)

        fg.description(info["description"])
        fg.image(url=info["thumbnails"][-1]["url"])

        for index, video in enumerate(info["entries"]):
            fe = fg.add_entry()
            fe.id(video["id"])
            fe.title(video["title"])
            fe.description(video["description"])
            fe.published(datetime.fromtimestamp(-index, timezone.utc))
            fe.enclosure(request.url_root + f"mp3/{video['id']}", 0, "audio/mpeg")

    response = Response(fg.rss_str(), mimetype="application/rss+xml")
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4280)
