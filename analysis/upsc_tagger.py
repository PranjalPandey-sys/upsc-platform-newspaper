"""analysis/upsc_tagger.py — UPSC Classification Stage."""
import logging
from services import ai_provider
from analysis.prompts import tagger_prompt
from storage.database import save_tags, log_ai_session
import config

logger = logging.getLogger(__name__)
SYSTEM = "You are a UPSC Civil Services exam expert. Classify news articles for UPSC preparation. Return only valid JSON."

async def tag_article(article):
    title  = article.get("title","")
    text   = article.get("full_text") or article.get("rss_summary","")
    source = article.get("source_name","Unknown")
    art_id = article["id"]
    if not text or len(text) < 50:
        return None
    prompt = tagger_prompt(title, text[:3000], source)
    raw, finish, latency = await ai_provider.call(SYSTEM, prompt, max_tokens=config.TOKENS_TAGGER, temperature=0.1, task_name="tagging")
    log_ai_session(art_id,"tagging",config.GEMINI_MODEL,len(prompt),len(raw),finish,latency,success=bool(raw))
    result = ai_provider.parse_json_response(raw, dict)
    if result:
        save_tags(art_id, result, config.GEMINI_MODEL)
        logger.info("Tagged | id=%d | gs=%s | prelims=%d", art_id, result.get("gs_papers"), result.get("prelims_relevance",0))
    return result
