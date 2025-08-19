import os
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import HTTPException
from urllib.parse import urlparse, parse_qs

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)
from yt_dlp import YoutubeDL

ytt_api = YouTubeTranscriptApi()
yt_dlp = YoutubeDL()

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


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


async def fetch_transcript_text(video: str) -> str:
    video_id = extract_video_id(video)
    if not video_id:
        raise HTTPException(
            status_code=400, detail="Invalid YouTube URL or Video ID.")
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


async def get_video_stats(video: str) -> dict:
    video_id = extract_video_id(video)
    if not video_id:
        raise HTTPException(
            status_code=400, detail="Invalid YouTube URL or Video ID.")
    info = yt_dlp.extract_info(video_id, download=False)
    return {
        "title": info.get("title"),
        "channel": info.get("uploader"),
        "upload_date": info.get("upload_date"),
        "duration": info.get("duration"),
        "views": info.get("view_count"),
        "likes": info.get("like_count"),
        "comments": info.get("comment_count")
    }


async def search_videos(query: str, max_results=5) -> list:
    search = f"ytsearch{max_results}:{query}"
    info = yt_dlp.extract_info(search, download=False)
    results = []
    for entry in info['entries']:
        results.append({
            "title": entry.get("title"),
            "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
            "channel": entry.get("uploader"),
        })
    return results


async def get_video_stats_official(video: str) -> dict:
    video_id = extract_video_id(video)
    if not video_id:
        raise HTTPException(
            status_code=400, detail="Invalid YouTube URL or Video ID.")
    try:
        url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics,snippet&id={video_id}&key={YOUTUBE_API_KEY}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()  # Raise error for bad status
            data = response.json()
            title = data['items'][0]['snippet']['title'] if data['items'] else 'No title found'
            return {
                "title": title,
                "video_id": video_id,
                "published_at": data['items'][0]['snippet']['publishedAt'] if data['items'] else 'No published date found',
                "statistics": data['items'][0]['statistics'] if data['items'] else {}
            }
    except Exception as e:
        return f"Error: {e}"


async def search_videos_official(query: str, max_results=5) -> list:
    try:
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&maxResults={max_results}&key={YOUTUBE_API_KEY}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()  # Raise error for bad status
            data = response.json()
            return [
                {
                    "title": item["snippet"]["title"],
                    "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                    "channel": item["snippet"]["channelTitle"],
                }
                for item in data.get("items", [])
                if item["id"]["kind"] == "youtube#video"
            ]
    except Exception as e:
        return f"Error: {e}"
