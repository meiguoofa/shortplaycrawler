import urllib.request
from datetime import datetime, timezone

from config import (
    CRAWL_CODE,
    DEFAULT_IMAGE_GEN_PROMPT,
    DEFAULT_TRANSLATE_SYSTEM_PROMPT,
    DEFAULT_TRANSLATE_USER_PROMPT,
    DOUBAO_DEFAULT_IMAGE_MODEL,
    EPISODES_URL,
    PLAY_URL,
    PLAY_URL_SLEEP,
    TOS_IMAGE_OBJECT_PREFIX,
    TRANSLATE_LANGS,
    VIDEO_QUALITY,
)
from crawler.client import build_url, fetch_with_retry
from crawler.play_url import _tos_fetch
from models import DailyNewDrama, EpisodeAsset, TranslationJob, get_session
from translate.doubao import translate_metadata
from translate.image_gen import generate_poster, upload_poster_to_tos


def _fetch_episodes_for_series(series_id: str) -> list[dict]:
    """Call book_hg endpoint to get episode list. Returns list of {video_id, title, firstPassTime}."""
    url = build_url(EPISODES_URL, {"book_id": series_id, "code": CRAWL_CODE})
    payload = fetch_with_retry(url, sleep_seconds=PLAY_URL_SLEEP)
    data = payload.get("data") or []
    return data if isinstance(data, list) else []


def _fetch_video_url(video_id: str, quality: str = VIDEO_QUALITY) -> str | None:
    """Call play_hg to get the CDN video URL for one episode."""
    url = build_url(PLAY_URL, {"video_id": video_id, "code": CRAWL_CODE, "level": quality})
    payload = fetch_with_retry(url, sleep_seconds=PLAY_URL_SLEEP)
    data = payload.get("data") or {}
    return data.get("video_url")


def _fetch_cover_bytes(cover_url: str) -> bytes | None:
    """Download original cover image bytes (for translation context if needed)."""
    try:
        req = urllib.request.Request(cover_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except Exception as e:
        print(f"  WARN: failed to fetch cover bytes: {e}")
        return None


def run_pipeline(
    daily_new_drama_id: int,
    target_lang: str,
    image_model: str = DOUBAO_DEFAULT_IMAGE_MODEL,
    image_prompt: str | None = None,
    translate_system_prompt: str | None = None,
    translate_user_prompt: str | None = None,
    batch_id: str | None = None,
    force_retry: bool = False,
    force_reprocess_episodes: bool = False,
) -> TranslationJob:
    """End-to-end: translate metadata + regenerate poster + upload ALL episodes to TOS.

    Args:
        daily_new_drama_id: DailyNewDrama.id
        target_lang: ISO code (en/zh/pt/pt-BR/id)
        image_model: doubao-seedream model name
        image_prompt: image prompt TEMPLATE (uses {target_lang} and {synopsis}); defaults to DEFAULT_IMAGE_GEN_PROMPT
        translate_system_prompt: translate system prompt template (uses {target_lang})
        translate_user_prompt: translate user prompt template (uses {title} and {description})
        batch_id: optional UUID grouping multiple dramas submitted together
        force_retry: if True, re-run translate + poster even if job already done.
                    Episode videos already uploaded to TOS are NEVER re-fetched (unless force_reprocess_episodes).
        force_reprocess_episodes: if True, re-fetch episode videos. DANGEROUS — only use if you want to
                                  re-upload (will skip already-uploaded ones anyway via EpisodeAsset check).
    Returns: TranslationJob
    """
    db = get_session()
    try:
        drama = db.query(DailyNewDrama).filter_by(id=daily_new_drama_id).first()
        if not drama:
            raise ValueError(f"DailyNewDrama id={daily_new_drama_id} not found")

        # Find or create TranslationJob (unique constraint on (daily_new_drama_id, target_lang))
        job = db.query(TranslationJob).filter_by(
            daily_new_drama_id=drama.id, target_lang=target_lang
        ).first()
        if not job:
            job = TranslationJob(
                daily_new_drama_id=drama.id,
                target_lang=target_lang,
                image_model=image_model,
                image_prompt_template=image_prompt or DEFAULT_IMAGE_GEN_PROMPT,
                translate_system_prompt=translate_system_prompt or DEFAULT_TRANSLATE_SYSTEM_PROMPT,
                translate_user_prompt=translate_user_prompt or DEFAULT_TRANSLATE_USER_PROMPT,
                status="pending",
                batch_id=batch_id,
            )
            db.add(job)
            db.commit()
        else:
            # Job exists — short-circuit if done and not retrying
            if job.status == "done" and not force_retry:
                print(f"  Skipping: job#{job.id} ({drama.title} → {target_lang}) already done")
                if batch_id and job.batch_id != batch_id:
                    job.batch_id = batch_id
                    db.commit()
                return job

            # Update batch_id + prompt templates for retry
            job.batch_id = batch_id
            if image_prompt is not None:
                job.image_prompt_template = image_prompt
            if translate_system_prompt is not None:
                job.translate_system_prompt = translate_system_prompt
            if translate_user_prompt is not None:
                job.translate_user_prompt = translate_user_prompt
            job.image_model = image_model
            job.status = "pending"
            job.error_message = None
            db.commit()

        lang_display = TRANSLATE_LANGS.get(target_lang, target_lang)
        print(f"\n=== Pipeline: {drama.title} → {lang_display} (model={image_model}) ===")
        if force_retry:
            print(f"  (force_retry=True; episode videos already in TOS will NOT be re-fetched)")

        # ── Step 1: translate title + description ──
        job.status = "translating"
        db.commit()
        try:
            translated_title, translated_desc, final_sys, final_usr = translate_metadata(
                drama.title,
                drama.description or "",
                target_lang,
                system_prompt_template=job.translate_system_prompt,
                user_prompt_template=job.translate_user_prompt,
            )
            job.translated_title = translated_title
            job.translated_desc = translated_desc
            job.translate_system_prompt_final = final_sys
            job.translate_user_prompt_final = final_usr
            db.commit()
            print(f"  Translated title: {translated_title}")
        except Exception as e:
            job.status = "failed"
            job.error_message = f"translate_metadata: {e}"[:500]
            db.commit()
            raise

        # ── Step 2: regenerate poster ──
        job.status = "poster_generating"
        db.commit()
        try:
            # Truncate synopsis to keep prompt under doubao's limit (avoids HTTP 400)
            synopsis_short = (translated_desc or "")[:200]
            template = job.image_prompt_template or image_prompt or DEFAULT_IMAGE_GEN_PROMPT
            final_prompt = template.format(
                target_lang=lang_display,
                synopsis=synopsis_short,
            )
            # Store both template and final value
            job.image_prompt_template = template
            job.image_prompt = final_prompt  # backward-compat: final value
            db.commit()

            poster_bytes = generate_poster(
                prompt=final_prompt,
                reference_image_url=drama.cover_url,
                model=image_model,
            )
            poster_obj_key = f"{TOS_IMAGE_OBJECT_PREFIX}/{drama.series_id}_{target_lang}.png"
            poster_url = upload_poster_to_tos(poster_bytes, poster_obj_key)
            job.poster_object_key = poster_obj_key
            job.poster_object_url = poster_url
            db.commit()
            print(f"  Poster uploaded: {poster_url} ({len(poster_bytes)} bytes)")
        except Exception as e:
            job.status = "failed"
            job.error_message = f"poster_gen: {e}"[:500]
            db.commit()
            raise

        # ── Step 3: fetch episode list + upload ALL episodes to TOS ──
        # CRITICAL: TOS already-uploaded episodes are NEVER re-fetched.
        # On force_retry, we skip the entire episodes phase (only translate + poster get redone).
        if force_retry and not force_reprocess_episodes:
            print(f"  Skipping episodes phase (force_retry=True; episodes already in TOS)")
        else:
            try:
                episodes_raw = _fetch_episodes_for_series(drama.series_id)
                print(f"  Episodes to upload: {len(episodes_raw)}")

                # Mark this stage so frontend can see "processing episodes"
                job.status = "processing_episodes"
                db.commit()

                for idx, ep in enumerate(episodes_raw, 1):
                    video_id = str(ep.get("video_id") or "")
                    if not video_id:
                        continue

                    # Hard check: skip if already uploaded (TOS videos are never re-fetched)
                    existing = db.query(EpisodeAsset).filter_by(
                        daily_new_drama_id=drama.id, video_id=video_id
                    ).first()
                    if existing and existing.status == "uploaded":
                        print(f"    [{idx}/{len(episodes_raw)}] ep{idx} ({video_id}) already uploaded, skipping")
                        continue

                    ea = existing or EpisodeAsset(
                        daily_new_drama_id=drama.id,
                        video_id=video_id,
                        episode_no=idx,
                        episode_title=ep.get("title", f"第{idx}集"),
                        status="pending",
                    )
                    if not existing:
                        db.add(ea)
                    db.commit()

                    try:
                        video_url = _fetch_video_url(video_id)
                        if not video_url:
                            ea.status = "failed"
                            ea.error_message = "No video_url in play_hg response"
                            db.commit()
                            continue

                        object_key = f"{TOS_IMAGE_OBJECT_PREFIX}/videos/{drama.series_id}/{idx:03d}_{video_id}.mp4"
                        object_url, file_size = _tos_fetch(video_url, object_key)
                        ea.object_key = object_key
                        ea.object_url = object_url
                        ea.file_size = file_size
                        ea.status = "uploaded"
                        ea.error_message = None
                        db.commit()
                        size_mb = (file_size or 0) / 1024 / 1024
                        print(f"    [{idx}/{len(episodes_raw)}] ep{idx} ({video_id}) → {size_mb:.1f}MB uploaded")
                    except Exception as e:
                        ea.status = "failed"
                        ea.error_message = str(e)[:500]
                        db.commit()
                        print(f"    [{idx}/{len(episodes_raw)}] ep{idx} ({video_id}) FAILED: {e}")
            except Exception as e:
                job.status = "failed"
                job.error_message = f"episodes: {e}"[:500]
                db.commit()
                raise

        # ── Done ──
        job.status = "done"
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        print(f"=== Pipeline done: job_id={job.id} ===")
        return job

    finally:
        db.close()
