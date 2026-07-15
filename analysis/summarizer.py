"""analysis/summarizer.py — Summary Generation Stage."""
import logging
from services import ai_provider
from analysis.prompts import summariser_prompt
from storage.database import save_summary, log_ai_session
import config

logger = logging.getLogger(__name__)
SYSTEM = "You are a senior UPSC content writer. Write accurate exam-focused summaries. Return only valid JSON."

async def summarise_article(article, tags=None):
    title    = article.get("title","")
    text     = article.get("full_text") or article.get("rss_summary","")
    source   = article.get("source_name","Unknown")
    art_id   = article["id"]
    gs_papers= (tags or {}).get("gs_papers",[])
    if not text or len(text) < 50:
        return None
    prompt = summariser_prompt(title, text[:4000], source, gs_papers)
    raw, finish, latency = await ai_provider.call(SYSTEM, prompt, max_tokens=config.TOKENS_SUMMARY, temperature=0.3, task_name="summary")
    log_ai_session(art_id,"summary",config.GEMINI_MODEL,len(prompt),len(raw),finish,latency,success=bool(raw))
    result = ai_provider.parse_json_response(raw, dict)
    if result:
        save_summary(art_id, result, config.GEMINI_MODEL)
        logger.info("Summarised | id=%d | chars=%d", art_id, len(result.get("short_summary","")))
    return result
