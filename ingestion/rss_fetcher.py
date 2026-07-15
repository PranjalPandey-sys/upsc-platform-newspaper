"""ingestion/rss_fetcher.py — RSS Feed Fetcher."""
import logging
from dataclasses import dataclass, field
import feedparser
from utils.helpers import clean_text, content_hash, parse_feed_date, truncate
import config

logger = logging.getLogger(__name__)

@dataclass
class RawArticle:
    source_id: int
    url: str
    title: str
    rss_summary: str
    author: str
    published_at: str
    content_hash: str = field(default="")
    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = content_hash(self.title, self.url)

def fetch_feed(source_id: int, rss_url: str, source_name: str) -> list:
    logger.info("Fetching %s", source_name)
    try:
        parsed = feedparser.parse(rss_url, request_headers={
            "User-Agent": "UPSC-Newspaper-Intelligence-Engine/1.0"
        })
    except Exception as exc:
        logger.error("feedparser failed | %s | %s", source_name, exc)
        return []
    if parsed.bozo and not parsed.entries:
        logger.warning("Malformed feed | %s", source_name)
        return []
    articles = []
    for entry in parsed.entries[:config.MAX_ARTICLES_PER_RUN]:
        try:
            a = _parse_entry(entry, source_id)
            if a:
                articles.append(a)
        except Exception:
            continue
    logger.info("Parsed %d articles from %s", len(articles), source_name)
    return articles

def _strip_html(text: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def _parse_entry(entry, source_id: int):
    url = (getattr(entry, "link", "") or getattr(entry, "id", "") or "").strip()
    if not url or not url.startswith("http"):
        return None
    title = clean_text(getattr(entry, "title", "")).strip()
    if not title:
        return None
    summary = _strip_html(getattr(entry, "summary", "") or getattr(entry, "description", "") or "")
    summary = truncate(summary, 1000)
    author = str(getattr(entry, "author", "") or "").strip()
    pub = ""
    if hasattr(entry, "published"):
        pub = parse_feed_date(entry.published)
    elif hasattr(entry, "updated"):
        pub = parse_feed_date(entry.updated)
    return RawArticle(source_id=source_id, url=url, title=title,
                      rss_summary=summary, author=author, published_at=pub)
