FROM python:3.8-slim

RUN apt-get update && apt-get install -y ffmpeg

RUN pip install Flask yt-dlp feedgen schedule

WORKDIR /app
ADD . .

EXPOSE 4280
CMD [ "python", "server.py" ]
