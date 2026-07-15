"""analysis/insight_extractor.py — Deep Insight Extraction Stage."""
import logging
from services import ai_provider
from analysis.prompts import insights_prompt
from storage.database import save_insights, log_ai_session
import config

logger = logging.getLogger(__name__)
SYSTEM = "You are a UPSC subject matter expert. Extract structured UPSC-relevant information. Return only valid JSON."

async def extract_insights(article, tags=None):
    title    = article.get("title","")
    text     = article.get("full_text") or article.get("rss_summary","")
    source   = article.get("source_name","Unknown")
    art_id   = article["id"]
    gs_papers= (tags or {}).get("gs_papers",[])
    if not text or len(text) < 100:
        return None
    prompt = insights_prompt(title, text[:5000], source, gs_papers)
    raw, finish, latency = await ai_provider.call(SYSTEM, prompt, max_tokens=config.TOKENS_INSIGHTS, temperature=0.2, task_name="insights")
    log_ai_session(art_id,"insights",config.GEMINI_MODEL,len(prompt),len(raw),finish,latency,success=bool(raw))
    result = ai_provider.parse_json_response(raw, dict)
    if result:
        save_insights(art_id, result, config.GEMINI_MODEL)
        logger.info("Insights | id=%d | schemes=%s", art_id, result.get("government_schemes",[])[:2])
    return result
