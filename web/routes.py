from fastapi import APIRouter, Request, Query
from sqlalchemy import func

from models import DramaSeries, DramaEpisode, get_session
from web.app import templates

router = APIRouter()


@router.get("/")
async def index(
    request: Request,
    genre_type: str = Query(None),
    category: str = Query(None),
    sort: str = Query("rank_order"),
    order: str = Query("asc"),
):
    db = get_session()
    try:
        query = db.query(DramaSeries)

        if genre_type:
            query = query.filter(DramaSeries.genre_type == genre_type)
        if category:
            query = query.filter(DramaSeries.category == category)

        # Sorting
        sort_col = getattr(DramaSeries, sort, DramaSeries.rank_order)
        if order == "desc":
            query = query.order_by(sort_col.desc(), DramaSeries.id.asc())
        else:
            query = query.order_by(sort_col.asc(), DramaSeries.id.asc())

        series_list = query.all()

        # Get episode counts for each series
        episode_counts = {}
        for s in series_list:
            count = db.query(DramaEpisode).filter_by(series_id=s.series_id).count()
            uploaded = db.query(DramaEpisode).filter_by(
                series_id=s.series_id, upload_status="uploaded"
            ).count()
            episode_counts[s.series_id] = {"total": count, "uploaded": uploaded}

        return templates.TemplateResponse("index.html", {
            "request": request,
            "series_list": series_list,
            "episode_counts": episode_counts,
            "current_genre_type": genre_type,
            "current_category": category,
            "current_sort": sort,
            "current_order": order,
        })
    finally:
        db.close()


@router.get("/series/{series_id}")
async def series_detail(request: Request, series_id: str):
    db = get_session()
    try:
        series = db.query(DramaSeries).filter_by(series_id=series_id).first()
        if not series:
            return {"error": "Series not found"}

        episodes = db.query(DramaEpisode).filter_by(
            series_id=series_id
        ).order_by(DramaEpisode.episode_no).all()

        return templates.TemplateResponse("detail.html", {
            "request": request,
            "series": series,
            "episodes": episodes,
        })
    finally:
        db.close()
