import os
from datetime import date as date_cls, datetime as dt, timedelta

from fastapi import APIRouter, Request, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import func as sa_func

from config import (
    DEFAULT_IMAGE_GEN_PROMPT,
    DEFAULT_TRANSLATE_SYSTEM_PROMPT,
    DEFAULT_TRANSLATE_USER_PROMPT,
    DOUBAO_DEFAULT_IMAGE_MODEL,
    DOUBAO_IMAGE_MODELS,
    TRANSLATE_LANGS,
)
from models import CartItem, DailyNewDrama, DramaEpisode, DramaSeries, EpisodeAsset, TranslationJob, get_session

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _serialize_drama(d: DailyNewDrama) -> dict:
    return {
        "id": d.id,
        "series_id": d.series_id,
        "fetch_date": d.fetch_date.isoformat() if d.fetch_date else None,
        "title": d.title,
        "cover_url": d.cover_url,
        "episode_cnt": d.episode_cnt,
        "category": d.category,
        "author": d.author,
        "description": d.description,
    }


def _serialize_cart(c: CartItem) -> dict:
    return {
        "id": c.id,
        "series_id": c.series_id,
        "title": c.title,
        "cover_url": c.cover_url,
        "episode_cnt": c.episode_cnt,
        "category": c.category,
        "author": c.author,
        "description": c.description,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _serialize_job(j: TranslationJob, drama: DailyNewDrama | None = None,
                    uploaded_eps: int = 0, total_eps: int = 0) -> dict:
    return {
        "id": j.id,
        "daily_new_drama_id": j.daily_new_drama_id,
        "target_lang": j.target_lang,
        "image_model": j.image_model,
        "image_prompt_template": j.image_prompt_template,
        "image_prompt_final": j.image_prompt,
        "translate_system_prompt": j.translate_system_prompt,
        "translate_user_prompt": j.translate_user_prompt,
        "translate_system_prompt_final": j.translate_system_prompt_final,
        "translate_user_prompt_final": j.translate_user_prompt_final,
        "status": j.status,
        "translated_title": j.translated_title,
        "translated_desc": j.translated_desc,
        "poster_object_url": j.poster_object_url,
        "error_message": j.error_message,
        "batch_id": j.batch_id,
        "created_at": j.created_at.isoformat() if j.created_at else None,
        "updated_at": j.updated_at.isoformat() if j.updated_at else None,
        "drama": _serialize_drama(drama) if drama else None,
        "uploaded_episodes": uploaded_eps,
        "total_episodes": total_eps,
    }


# ── Config endpoint ───────────────────────────────────────────────────────────

@router.get("/api/config/defaults")
async def api_config_defaults():
    """Return all default prompts, models, languages for the frontend."""
    return JSONResponse({
        "langs": TRANSLATE_LANGS,
        "image_models": DOUBAO_IMAGE_MODELS,
        "default_image_model": DOUBAO_DEFAULT_IMAGE_MODEL,
        "default_image_prompt": DEFAULT_IMAGE_GEN_PROMPT,
        "default_translate_system_prompt": DEFAULT_TRANSLATE_SYSTEM_PROMPT,
        "default_translate_user_prompt": DEFAULT_TRANSLATE_USER_PROMPT,
    })


# ── Series (legacy ranking DB) ───────────────────────────────────────────────

@router.get("/api/series")
async def api_series_list(
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
        sort_col = getattr(DramaSeries, sort, DramaSeries.rank_order)
        if order == "desc":
            query = query.order_by(sort_col.desc(), DramaSeries.id.asc())
        else:
            query = query.order_by(sort_col.asc(), DramaSeries.id.asc())

        series_list = query.all()
        result = []
        for s in series_list:
            total = db.query(DramaEpisode).filter_by(series_id=s.series_id).count()
            uploaded = db.query(DramaEpisode).filter_by(
                series_id=s.series_id, upload_status="uploaded"
            ).count()
            result.append({
                "id": s.id,
                "series_id": s.series_id,
                "genre_type": s.genre_type,
                "category": s.category,
                "title": s.title,
                "cover_url": s.cover_url,
                "episode_cnt": s.episode_cnt,
                "play_cnt": s.play_cnt,
                "score": s.score,
                "rank_order": s.rank_order,
                "hot_content": s.hot_content,
                "author": s.author,
                "duration": s.duration,
                "detail_category": s.detail_category,
                "total_episodes": s.total_episodes,
                "episodes_total": total,
                "episodes_uploaded": uploaded,
            })
        return JSONResponse({"series": result, "count": len(result)})
    finally:
        db.close()


@router.get("/api/series/{series_id}")
async def api_series_detail(series_id: str):
    db = get_session()
    try:
        series = db.query(DramaSeries).filter_by(series_id=series_id).first()
        if not series:
            return JSONResponse({"error": "Series not found"}, status_code=404)
        episodes = db.query(DramaEpisode).filter_by(
            series_id=series_id
        ).order_by(DramaEpisode.episode_no).all()
        return JSONResponse({
            "series": {
                "id": series.id,
                "series_id": series.series_id,
                "genre_type": series.genre_type,
                "category": series.category,
                "title": series.title,
                "cover_url": series.cover_url,
                "episode_cnt": series.episode_cnt,
                "play_cnt": series.play_cnt,
                "score": series.score,
                "video_desc": series.video_desc,
                "author": series.author,
                "copyright": series.copyright,
                "duration": series.duration,
                "detail_category": series.detail_category,
                "detail_desc": series.detail_desc,
                "book_pic": series.book_pic,
                "total_episodes": series.total_episodes,
            },
            "episodes": [
                {
                    "id": e.id,
                    "video_id": e.video_id,
                    "episode_no": e.episode_no,
                    "episode_title": e.episode_title,
                    "upload_status": e.upload_status,
                    "object_storage_url": e.object_storage_url,
                    "file_size": e.file_size,
                    "error_message": e.error_message,
                }
                for e in episodes
            ],
        })
    finally:
        db.close()


# ── Daily new dramas ──────────────────────────────────────────────────────────

@router.get("/api/daily-new")
async def api_daily_new_list(date: str = Query(None)):
    """List daily-new dramas for a given date (default: today)."""
    if date:
        try:
            target_date = dt.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            target_date = date_cls.today()
    else:
        target_date = date_cls.today()

    db = get_session()
    try:
        dramas = db.query(DailyNewDrama).filter_by(fetch_date=target_date).order_by(DailyNewDrama.id).all()
        drama_ids = [d.id for d in dramas]
        job_map = {}
        if drama_ids:
            for j in db.query(TranslationJob).filter(
                TranslationJob.daily_new_drama_id.in_(drama_ids)
            ).all():
                job_map.setdefault(j.daily_new_drama_id, []).append(j)

        return JSONResponse({
            "target_date": target_date.isoformat(),
            "prev_date": (target_date - timedelta(days=1)).isoformat(),
            "next_date": (target_date + timedelta(days=1)).isoformat(),
            "dramas": [_serialize_drama(d) for d in dramas],
            "job_map": {
                str(k): [
                    {
                        "id": j.id,
                        "target_lang": j.target_lang,
                        "status": j.status,
                        "batch_id": j.batch_id,
                    }
                    for j in vs
                ]
                for k, vs in job_map.items()
            },
        })
    finally:
        db.close()


class RunPipelineRequest(BaseModel):
    drama_ids: list[int]
    target_lang: str
    image_model: str = DOUBAO_DEFAULT_IMAGE_MODEL
    image_prompt: str | None = None
    translate_system_prompt: str | None = None
    translate_user_prompt: str | None = None
    batch_id: str | None = None
    force_retry: bool = False
    force_reprocess_episodes: bool = False


@router.post("/api/daily-new/run")
async def api_daily_new_run(req: RunPipelineRequest):
    """Trigger pipeline for selected dramas ASYNCHRONOUSLY."""
    import threading
    from pipeline import run_pipeline as _run_pipeline

    db = get_session()
    try:
        for did in req.drama_ids:
            drama = db.query(DailyNewDrama).filter_by(id=did).first()
            if not drama:
                continue
            existing = db.query(TranslationJob).filter_by(
                daily_new_drama_id=drama.id, target_lang=req.target_lang
            ).first()
            if existing:
                if existing.status == "done" and not req.force_retry:
                    if req.batch_id:
                        existing.batch_id = req.batch_id
                    continue
                existing.batch_id = req.batch_id
                existing.status = "pending"
                existing.error_message = None
                if req.image_prompt is not None:
                    existing.image_prompt_template = req.image_prompt
                if req.translate_system_prompt is not None:
                    existing.translate_system_prompt = req.translate_system_prompt
                if req.translate_user_prompt is not None:
                    existing.translate_user_prompt = req.translate_user_prompt
                existing.image_model = req.image_model
            else:
                job = TranslationJob(
                    daily_new_drama_id=drama.id,
                    target_lang=req.target_lang,
                    image_model=req.image_model,
                    image_prompt_template=req.image_prompt or DEFAULT_IMAGE_GEN_PROMPT,
                    translate_system_prompt=req.translate_system_prompt or DEFAULT_TRANSLATE_SYSTEM_PROMPT,
                    translate_user_prompt=req.translate_user_prompt or DEFAULT_TRANSLATE_USER_PROMPT,
                    status="pending",
                    batch_id=req.batch_id,
                )
                db.add(job)
        db.commit()
    finally:
        db.close()

    def _bg_run():
        for did in req.drama_ids:
            try:
                _run_pipeline(
                    daily_new_drama_id=did,
                    target_lang=req.target_lang,
                    image_model=req.image_model,
                    image_prompt=req.image_prompt,
                    translate_system_prompt=req.translate_system_prompt,
                    translate_user_prompt=req.translate_user_prompt,
                    batch_id=req.batch_id,
                    force_retry=req.force_retry,
                    force_reprocess_episodes=req.force_reprocess_episodes,
                )
            except Exception as e:
                import sys
                print(f"[batch {req.batch_id}] drama {did} FAILED: {e}", file=sys.stderr, flush=True)

    t = threading.Thread(target=_bg_run, daemon=True)
    t.start()

    return JSONResponse({
        "batch_id": req.batch_id,
        "drama_ids": req.drama_ids,
        "status": "started",
        "force_retry": req.force_retry,
    })


class BackfillRequest(BaseModel):
    start_date: str
    end_date: str


@router.post("/api/daily-new/backfill")
async def api_daily_new_backfill(req: BackfillRequest):
    """Crawl daily-new dramas for every date in [start, end] inclusive."""
    from crawler.daily_new import crawl_daily_new_range
    try:
        start = dt.strptime(req.start_date, "%Y-%m-%d").date()
        end = dt.strptime(req.end_date, "%Y-%m-%d").date()
    except ValueError as e:
        return JSONResponse({"error": f"invalid date: {e}"}, status_code=400)
    if start > end:
        return JSONResponse({"error": "start_date > end_date"}, status_code=400)
    total = crawl_daily_new_range(start, end)
    return JSONResponse({"total_inserted": total, "start": req.start_date, "end": req.end_date})


# ── Search ────────────────────────────────────────────────────────────────────

@router.get("/api/search/platforms")
async def api_search_platforms():
    """Return list of search platforms for the frontend dropdown."""
    from config import SEARCH_PLATFORMS
    return JSONResponse({
        "platforms": [
            {"value": p["platform"], "label": p["label"]}
            for p in SEARCH_PLATFORMS
        ],
    })


@router.get("/api/search")
async def api_search(
    q: str = Query(..., min_length=1),
    limit: int | None = Query(None, ge=1, le=100),
    platform: str = Query(...),
):
    """Search across one platform (selected by `platform` key). limit=N caps per keyword."""
    from crawler.search import fetch_search_all, normalize_search_item
    try:
        raw = fetch_search_all(q, per_keyword_limit=limit, platform_key=platform)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    items = [normalize_search_item(r) for r in raw]
    return JSONResponse({"items": items, "count": len(items)})


# ── Pending cart ─────────────────────────────────────────────────────────────

class CartAddItem(BaseModel):
    series_id: str
    title: str
    cover_url: str | None = None
    episode_cnt: int | None = None
    category: str | None = None
    author: str | None = None
    description: str | None = None
    raw_payload: str | None = None


class CartAddRequest(BaseModel):
    items: list[CartAddItem]


@router.get("/api/pending-cart")
async def api_cart_list():
    """List all cart items, newest first."""
    db = get_session()
    try:
        rows = db.query(CartItem).order_by(CartItem.id.desc()).all()
        return JSONResponse({"items": [_serialize_cart(c) for c in rows], "count": len(rows)})
    finally:
        db.close()


@router.post("/api/pending-cart")
async def api_cart_add(req: CartAddRequest):
    """Add items to cart (skip if series_id already in cart)."""
    db = get_session()
    try:
        added = 0
        for it in req.items:
            if not it.series_id:
                continue
            if db.query(CartItem).filter_by(series_id=it.series_id).first():
                continue
            db.add(CartItem(
                series_id=it.series_id,
                title=it.title,
                cover_url=it.cover_url,
                episode_cnt=it.episode_cnt,
                category=it.category,
                author=it.author,
                description=it.description,
                raw_payload=it.raw_payload,
            ))
            added += 1
        db.commit()
        return JSONResponse({"added": added})
    finally:
        db.close()


@router.delete("/api/pending-cart/{item_id}")
async def api_cart_remove(item_id: int):
    """Remove one cart item by id; item_id=0 clears all."""
    db = get_session()
    try:
        if item_id == 0:
            n = db.query(CartItem).delete()
        else:
            n = db.query(CartItem).filter_by(id=item_id).delete()
        db.commit()
        return JSONResponse({"deleted": n})
    finally:
        db.close()


class CartCheckoutRequest(BaseModel):
    target_lang: str
    image_model: str = DOUBAO_DEFAULT_IMAGE_MODEL
    image_prompt: str | None = None
    translate_system_prompt: str | None = None
    translate_user_prompt: str | None = None


@router.post("/api/pending-cart/checkout")
async def api_cart_checkout(req: CartCheckoutRequest):
    """Move cart items into DailyNewDrama(fetch_date=today) + run pipeline + clear cart."""
    import threading
    import uuid
    from datetime import date as date_cls

    from pipeline import run_pipeline as _run_pipeline

    db = get_session()
    try:
        cart_items = db.query(CartItem).order_by(CartItem.id).all()
        if not cart_items:
            return JSONResponse({"error": "cart is empty"}, status_code=400)

        batch_id = str(uuid.uuid4())
        drama_ids: list[int] = []
        today = date_cls.today()

        for c in cart_items:
            existing = db.query(DailyNewDrama).filter_by(
                series_id=c.series_id, fetch_date=today
            ).first()
            if existing:
                drama_ids.append(existing.id)
                continue
            drama = DailyNewDrama(
                series_id=c.series_id,
                fetch_date=today,
                title=c.title,
                cover_url=c.cover_url,
                episode_cnt=c.episode_cnt,
                category=c.category,
                author=c.author,
                description=c.description,
                raw_payload=c.raw_payload,
            )
            db.add(drama)
            db.flush()
            drama_ids.append(drama.id)

        for did in drama_ids:
            existing_job = db.query(TranslationJob).filter_by(
                daily_new_drama_id=did, target_lang=req.target_lang
            ).first()
            if existing_job:
                existing_job.batch_id = batch_id
                existing_job.status = "pending"
                existing_job.error_message = None
                if req.image_prompt is not None:
                    existing_job.image_prompt_template = req.image_prompt
                if req.translate_system_prompt is not None:
                    existing_job.translate_system_prompt = req.translate_system_prompt
                if req.translate_user_prompt is not None:
                    existing_job.translate_user_prompt = req.translate_user_prompt
                existing_job.image_model = req.image_model
                continue
            db.add(TranslationJob(
                daily_new_drama_id=did,
                target_lang=req.target_lang,
                image_model=req.image_model,
                image_prompt_template=req.image_prompt or DEFAULT_IMAGE_GEN_PROMPT,
                translate_system_prompt=req.translate_system_prompt or DEFAULT_TRANSLATE_SYSTEM_PROMPT,
                translate_user_prompt=req.translate_user_prompt or DEFAULT_TRANSLATE_USER_PROMPT,
                status="pending",
                batch_id=batch_id,
            ))

        db.query(CartItem).delete()
        db.commit()
    finally:
        db.close()

    def _bg_run():
        for did in drama_ids:
            try:
                _run_pipeline(
                    daily_new_drama_id=did,
                    target_lang=req.target_lang,
                    image_model=req.image_model,
                    image_prompt=req.image_prompt,
                    translate_system_prompt=req.translate_system_prompt,
                    translate_user_prompt=req.translate_user_prompt,
                    batch_id=batch_id,
                )
            except Exception as e:
                import sys
                print(f"[batch {batch_id}] drama {did} FAILED: {e}", file=sys.stderr, flush=True)

    threading.Thread(target=_bg_run, daemon=True).start()
    return JSONResponse({
        "batch_id": batch_id,
        "drama_ids": drama_ids,
        "status": "started",
    })


# ── Batches ──────────────────────────────────────────────────────────────────

@router.get("/api/daily-new/batches")
async def api_batches_list():
    """List all batches (grouped by batch_id)."""
    db = get_session()
    try:
        rows = db.query(
            TranslationJob.batch_id,
            sa_func.count(TranslationJob.id).label("job_count"),
            sa_func.min(TranslationJob.created_at).label("created_at"),
            sa_func.min(TranslationJob.target_lang).label("target_lang"),
        ).filter(
            TranslationJob.batch_id.isnot(None)
        ).group_by(
            TranslationJob.batch_id
        ).order_by(
            sa_func.min(TranslationJob.created_at).desc()
        ).all()

        batches = []
        for r in rows:
            jobs = db.query(TranslationJob).filter_by(batch_id=r.batch_id).all()
            drama_ids = [j.daily_new_drama_id for j in jobs]
            dramas = db.query(DailyNewDrama).filter(DailyNewDrama.id.in_(drama_ids)).all() if drama_ids else []
            done = sum(1 for j in jobs if j.status == "done")
            failed = sum(1 for j in jobs if j.status == "failed")
            pending = sum(1 for j in jobs if j.status not in ("done", "failed"))

            ep_total = db.query(EpisodeAsset).filter(
                EpisodeAsset.daily_new_drama_id.in_(drama_ids)
            ).count() if drama_ids else 0
            ep_uploaded = db.query(EpisodeAsset).filter(
                EpisodeAsset.daily_new_drama_id.in_(drama_ids),
                EpisodeAsset.status == "uploaded",
            ).count() if drama_ids else 0

            batches.append({
                "batch_id": r.batch_id,
                "job_count": r.job_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "target_lang": r.target_lang,
                "done_count": done,
                "failed_count": failed,
                "pending_count": pending,
                "dramas": [_serialize_drama(d) for d in dramas],
                "ep_uploaded": ep_uploaded,
                "ep_total": ep_total,
            })
        return JSONResponse({"batches": batches, "count": len(batches)})
    finally:
        db.close()


@router.get("/api/daily-new/batches/{batch_id}")
async def api_batch_detail(batch_id: str):
    """Return one batch's jobs with all prompt templates + final values."""
    db = get_session()
    try:
        jobs = db.query(TranslationJob).filter_by(batch_id=batch_id).order_by(TranslationJob.id).all()
        if not jobs:
            return JSONResponse({"error": f"batch {batch_id} not found"}, status_code=404)
        job_data = []
        for j in jobs:
            drama = db.query(DailyNewDrama).filter_by(id=j.daily_new_drama_id).first()
            eps = db.query(EpisodeAsset).filter_by(daily_new_drama_id=j.daily_new_drama_id).all()
            uploaded = sum(1 for e in eps if e.status == "uploaded")
            job_data.append(_serialize_job(j, drama, uploaded, len(eps)))
        return JSONResponse({
            "batch_id": batch_id,
            "jobs": job_data,
            "total_jobs": len(job_data),
            "done_count": sum(1 for j in job_data if j["status"] == "done"),
            "failed_count": sum(1 for j in job_data if j["status"] == "failed"),
            "pending_count": sum(1 for j in job_data if j["status"] not in ("done", "failed")),
        })
    finally:
        db.close()


@router.get("/api/daily-new/batches/{batch_id}/export")
async def api_batch_export(batch_id: str, format: str = "csv"):
    """Export all jobs in a batch as a single CSV/XLSX file."""
    from exporter import export_batch
    try:
        path = export_batch(batch_id, format)
        return FileResponse(path, filename=path.split("/")[-1])
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=404)


# ── Jobs (all TranslationJob) ────────────────────────────────────────────────

@router.get("/api/daily-new/jobs")
async def api_jobs_list():
    """List all translation jobs (most recent first)."""
    db = get_session()
    try:
        jobs = db.query(TranslationJob).order_by(TranslationJob.id.desc()).all()
        result = []
        for j in jobs:
            drama = db.query(DailyNewDrama).filter_by(id=j.daily_new_drama_id).first()
            eps = db.query(EpisodeAsset).filter_by(daily_new_drama_id=j.daily_new_drama_id).all()
            uploaded = sum(1 for e in eps if e.status == "uploaded")
            result.append(_serialize_job(j, drama, uploaded, len(eps)))
        return JSONResponse({"jobs": result, "count": len(result)})
    finally:
        db.close()


@router.get("/api/daily-new/jobs/export")
async def api_jobs_export(format: str = "csv", job_ids: str = Query(None)):
    """Export jobs. ?format=csv|xlsx&job_ids=1,2,3 (omit for all)."""
    from exporter import export_jobs
    db = get_session()
    try:
        q = db.query(TranslationJob)
        if job_ids:
            ids = [int(x) for x in job_ids.split(",") if x.strip().isdigit()]
            q = q.filter(TranslationJob.id.in_(ids))
        jobs = q.all()
        if not jobs:
            return JSONResponse({"error": "no jobs"}, status_code=404)
        path = export_jobs(jobs, format)
        return FileResponse(path, filename=path.split("/")[-1])
    finally:
        db.close()


# ── SPA fallback (must be LAST) ──────────────────────────────────────────────

@router.get("/{path:path}")
async def spa_fallback(path: str):
    """All non-API paths return the SPA index.html (Vue Router handles routing)."""
    # Don't intercept /api/* (already matched above) or /static/*
    if path.startswith("api/") or path.startswith("static/"):
        return JSONResponse({"error": "not found"}, status_code=404)
    index_path = os.path.join(BASE_DIR, "static", "index.html")
    if not os.path.exists(index_path):
        return JSONResponse({"error": "SPA index.html not built"}, status_code=500)
    return FileResponse(index_path)
