from fastapi import FastAPI, HTTPException, Query

from utils import (
    get_page_title,
    fetch_transcript_text,
    get_video_stats,
    search_videos,
    get_video_stats_official,
    search_videos_official
)

app = FastAPI()


@app.get("/api/v1/transcript")
async def get_transcript(video: str = Query(..., description="YouTube URL or Video ID")):
    text = await fetch_transcript_text(video)
    title = await get_page_title(video)
    return {"status": "success", "data": {"title": title, "transcript": text}}


@app.get("/api/v1/search")
async def get_videos(
    query: str = Query(..., description="Search query"),
    max_results: int = Query(
        5, description="Maximum number of results to return")
):
    results = await search_videos(query, max_results)
    return {"status": "success", "data": results}


@app.get("/api/v1/video_info")
async def get_video_info(video: str = Query(..., description="YouTube URL or Video ID")):
    info = await get_video_stats(video)
    return {"status": "success", "data": info}


@app.get("/api/v2/search")
async def get_videos(
    query: str = Query(..., description="Search query"),
    max_results: int = Query(
        5, description="Maximum number of results to return")
):
    results = await search_videos_official(query, max_results)
    return {"status": "success", "data": results}


@app.get("/api/v2/video_info")
async def get_video_info(video: str = Query(..., description="YouTube URL or Video ID")):
    video_info = await get_video_stats_official(video)
    if not video_info:
        raise HTTPException(
            status_code=404, detail="Video not found.")
    return {"status": "success", "data": video_info}
