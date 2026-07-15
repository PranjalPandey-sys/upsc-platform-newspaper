"""ingestion/content_extractor.py — Article Content Extractor."""
import logging
import asyncio
import config
from utils.helpers import clean_text, truncate

logger = logging.getLogger(__name__)
_trafilatura = None

def _get_t():
    global _trafilatura
    if _trafilatura is None:
        try:
            import trafilatura
            _trafilatura = trafilatura
        except ImportError:
            logger.error("trafilatura not installed")
    return _trafilatura

async def extract_article_text(url: str, rss_summary: str = "") -> tuple:
    if not url or not url.startswith("http"):
        return rss_summary, "skipped"
    try:
        text = await asyncio.to_thread(_extract_sync, url)
    except Exception as exc:
        logger.debug("Extraction error | %s | %s", url[:80], exc)
        return rss_summary, "failed"
    if text and len(text) > 200:
        return truncate(clean_text(text), config.MAX_CONTENT_CHARS), "done"
    if rss_summary and len(rss_summary) > 50:
        return rss_summary, "skipped"
    return "", "skipped"

def _extract_sync(url: str):
    t = _get_t()
    if not t:
        return None
    try:
        downloaded = t.fetch_url(url)
        if not downloaded:
            return None
        return t.extract(downloaded, include_comments=False,
                         include_tables=False, favor_precision=True)
    except Exception:
        return None

def estimate_quality(text: str, rss_summary: str) -> str:
    n = len(text or "")
    if n > 2000: return "rich"
    if n > 400:  return "partial"
    if len(rss_summary or "") > 100: return "rss_only"
    return "minimal"
