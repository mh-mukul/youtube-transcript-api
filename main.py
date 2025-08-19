import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from fastapi import FastAPI, HTTPException, Query

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

from yt_dlp import YoutubeDL

app = FastAPI()
ytt_api = YouTubeTranscriptApi()


async def get_page_title(url):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()  # Raise error for bad status
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string.strip() if soup.title else 'No title found'
            return title
    except Exception as e:
        return f"Error: {e}"


def extract_video_id(url_or_id: str) -> str:
    parsed_url = urlparse(url_or_id)
    if parsed_url.netloc == "youtu.be":
        return parsed_url.path[1:]
    if parsed_url.netloc in ("www.youtube.com", "youtube.com"):
        query = parse_qs(parsed_url.query)
        return query.get("v", [None])[0]
    return url_or_id


async def fetch_transcript_text(video_id: str) -> str:
    try:
        transcript = ytt_api.fetch(video_id=video_id, languages=["en"])
        print(f"[DEBUG] Transcript: {transcript}")
        return " ".join(snippet.text for snippet in transcript.snippets)
    except TranscriptsDisabled:
        raise HTTPException(
            status_code=400, detail="Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise HTTPException(
            status_code=404, detail="No English transcript found for this video.")
    except VideoUnavailable:
        raise HTTPException(
            status_code=404, detail="The video is unavailable.")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}")


async def get_video_stats(video_id: str) -> dict:
    # Using synchronous YoutubeDL for now - could be moved to a thread if needed
    with YoutubeDL() as ydl:
        info = ydl.extract_info(video_id, download=False)
        return {
            "title": info.get("title"),
            "channel": info.get("uploader"),
            "upload_date": info.get("upload_date"),
            "duration": info.get("duration"),
            "views": info.get("view_count"),
            "likes": info.get("like_count"),
            "comments": info.get("comment_count")
        }


@app.get("/api/transcript")
async def get_transcript(video: str = Query(..., description="YouTube URL or Video ID")):
    video_id = extract_video_id(video)
    if not video_id:
        raise HTTPException(
            status_code=400, detail="Invalid YouTube URL or Video ID.")
    text = await fetch_transcript_text(video_id)
    title = await get_page_title(video)
    return {"title": title, "video_id": video_id, "transcript": text}


@app.get("/api/video_info")
async def get_video_info(video: str = Query(..., description="YouTube URL or Video ID")):
    video_id = extract_video_id(video)
    if not video_id:
        raise HTTPException(
            status_code=400, detail="Invalid YouTube URL or Video ID.")
    info = await get_video_stats(video_id)
    title = await get_page_title(video)
    return {"title": title, "video_id": video_id, "info": info}
