import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import schedule
from flask import Flask, Response, request, send_file 
from yt_dlp import YoutubeDL
from feedgen.feed import FeedGenerator

app = Flask(__name__)

def download_from_youtube(video_id):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{tempfile.gettempdir()}/%(id)s.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"http://www.youtube.com/watch?v={video_id}"])

@app.route('/', methods=['GET', 'POST'])
def index():
    return '''
        <form method="post">
            <label for="name">video id:</label>
            <input type="text" id="id" name="id">
        <button type="button" onclick="window.location.href='/mp3/' + document.getElementById('id').value;">mp3</button>
        <button type="button" onclick="window.location.href='/feed/' + document.getElementById('id').value;">Feed</button>
        </form>
    '''
@app.route("/mp3/<video_id>")
def stream_mp3(video_id):
    file_path = Path(tempfile.gettempdir()) / f"{video_id}.mp3"
    if not file_path.is_file():
        download_from_youtube(video_id)
    return send_file(str(file_path), mimetype="audio/mpeg")

@app.route("/feed/<channel_id>")
def feed(channel_id):
    channel_id = channel_id.lower()
    youtube_url = f"https://www.youtube.com/{channel_id}"

    fg = FeedGenerator()
    fg.load_extension("podcast")

    with YoutubeDL(dict(extract_flat="in_playlist")) as ydl:
        info = ydl.extract_info(f"{youtube_url}/videos", download=False)

        fg.id(f"yt:{channel_id}")
        fg.title(info["channel"])
        fg.description(info["description"])
        fg.link(href=youtube_url)
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

def cleanup_mp3():
    for file in Path(tempfile.gettempdir()).glob("*.mp3"):
        if datetime.fromtimestamp(file.stat().st_mtime) < datetime.now() - timedelta(days=1):
            file.unlink()

if __name__ == "__main__":
    schedule.every().day.at("00:00:00").do(cleanup_mp3)
    app.run(host="0.0.0.0", port=4280, threaded=True)
