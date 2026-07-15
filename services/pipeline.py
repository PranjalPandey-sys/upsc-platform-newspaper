"""services/pipeline.py — Full Article Processing Pipeline."""
import asyncio, logging
import config
from ingestion.rss_fetcher import fetch_feed
from ingestion.content_extractor import extract_article_text
from storage.database import (
    get_active_sources, update_source_fetched,
    article_exists, insert_article,
    get_pending_extraction, update_article_extraction,
    get_pending_analysis, update_article_analysis_status,
    get_article, start_ingestion_run, finish_ingestion_run,
)
from utils.helpers import iso_now

logger = logging.getLogger(__name__)

async def run_ingestion():
    sources = get_active_sources()
    logger.info("Ingestion started | sources=%d", len(sources))
    total_new = total_dup = total_fail = 0
    for source in sources:
        source_id = source["id"]
        run_id = start_ingestion_run(source_id)
        s_new = s_dup = s_fail = 0
        try:
            articles = fetch_feed(source_id, source["rss_url"], source["name"])
            for raw in articles:
                if article_exists(raw.content_hash):
                    s_dup += 1; continue
                new_id = insert_article({
                    "content_hash": raw.content_hash, "source_id": source_id,
                    "url": raw.url, "title": raw.title, "rss_summary": raw.rss_summary,
                    "author": raw.author, "published_at": raw.published_at,
                })
                if new_id: s_new += 1
                else: s_dup += 1
            update_source_fetched(source_id)
            finish_ingestion_run(run_id, s_new+s_dup, s_new, s_dup, 0, "success")
            logger.info("Source done | %s | new=%d dup=%d", source["name"], s_new, s_dup)
        except Exception as exc:
            finish_ingestion_run(run_id, 0, 0, 0, 1, "failed", str(exc))
            logger.exception("Source failed | %s | %s", source["name"], exc)
            s_fail += 1
        total_new += s_new; total_dup += s_dup; total_fail += s_fail
    logger.info("Ingestion complete | new=%d dup=%d failed=%d", total_new, total_dup, total_fail)
    return {"new": total_new, "duplicate": total_dup, "failed": total_fail}

async def run_content_extraction(batch_size=20):
    pending = get_pending_extraction(batch_size)
    if not pending:
        logger.info("No articles pending extraction"); return 0
    logger.info("Extracting text | count=%d", len(pending))
    semaphore = asyncio.Semaphore(5)
    async def _one(article):
        async with semaphore:
            art_id = article["id"]
            try:
                text, status = await extract_article_text(article["url"], article.get("rss_summary",""))
                update_article_extraction(art_id, text, status)
            except Exception as exc:
                logger.warning("Extraction error | id=%d | %s", art_id, exc)
                update_article_extraction(art_id, article.get("rss_summary",""), "failed")
    await asyncio.gather(*[_one(a) for a in pending])
    return len(pending)

async def run_analysis(batch_size=None):
    limit = batch_size or config.ANALYSIS_BATCH_SIZE
    pending = get_pending_analysis(limit)
    if not pending:
        logger.info("No articles pending analysis"); return 0
    logger.info("Analysis started | count=%d", len(pending))
    done = failed = 0
    for article in pending:
        art_id = article["id"]
        update_article_analysis_status(art_id, "processing")
        try:
            success = await _analyse_one(article)
            update_article_analysis_status(art_id, "done" if success else "failed")
            if success: done += 1
            else: failed += 1
        except Exception as exc:
            logger.exception("Analysis error | id=%d | %s", art_id, exc)
            update_article_analysis_status(art_id, "failed")
            failed += 1
    logger.info("Analysis complete | done=%d failed=%d", done, failed)
    return done

async def _analyse_one(article):
    from analysis.upsc_tagger import tag_article
    from analysis.summarizer import summarise_article
    from analysis.insight_extractor import extract_insights
    from analysis.question_generator import generate_questions, link_pyqs
    from storage.database import get_db

    art_id = article["id"]
    if not article.get("source_name"):
        with get_db() as conn:
            row = conn.execute("SELECT name FROM sources WHERE id=?", (article["source_id"],)).fetchone()
            article["source_name"] = row["name"] if row else "Unknown"

    logger.info("Analysing | id=%d | %s", art_id, article["title"][:60])
    tags = await tag_article(article)
    if not tags:
        logger.warning("Tagging failed | id=%d", art_id); return False
    summary  = await summarise_article(article, tags)
    text_len = len(article.get("full_text") or article.get("rss_summary",""))
    insights = await extract_insights(article, tags) if text_len >= 200 else None
    if summary or text_len >= 150:
        await generate_questions(article, tags, summary, insights)
    try:
        if insights and tags.get("prelims_relevance",0) >= 6:
            await link_pyqs(article, tags, insights)
    except Exception:
        pass
    return True

async def regenerate_article(article_id):
    from storage.database import clear_ai_analysis, get_full_article_detail
    logger.info("Regenerating | id=%d", article_id)
    clear_ai_analysis(article_id)
    detail = get_full_article_detail(article_id)
    if not detail: return False
    success = await _analyse_one(detail)
    update_article_analysis_status(article_id, "done" if success else "failed")
    return success
