"""analysis/question_generator.py — Question Generation Stage."""
import logging
from services import ai_provider
from analysis.prompts import questions_prompt, pyq_linker_prompt
from storage.database import save_questions, save_pyq_connections, log_ai_session
import config

logger = logging.getLogger(__name__)
SYS_Q   = "You are a UPSC question paper setter. Generate authentic UPSC-pattern questions. Return only a valid JSON array."
SYS_PYQ = "You are a UPSC expert with complete knowledge of previous year papers. Identify genuine connections. Return only a valid JSON array."

async def generate_questions(article, tags=None, summary=None, insights=None):
    art_id    = article["id"]
    title     = article.get("title","")
    gs_papers = (tags or {}).get("gs_papers",[])
    short_sum = (summary or {}).get("short_summary", article.get("rss_summary",""))
    ins       = insights or {}
    if not title: return []
    if (tags or {}).get("prelims_relevance",0) < 4 and (tags or {}).get("mains_relevance",0) < 4:
        return []
    prompt = questions_prompt(title, short_sum, ins, gs_papers)
    raw, finish, latency = await ai_provider.call(SYS_Q, prompt, max_tokens=config.TOKENS_QUESTIONS, temperature=0.4, task_name="questions")
    log_ai_session(art_id,"questions",config.GEMINI_MODEL,len(prompt),len(raw),finish,latency,success=bool(raw))
    questions = ai_provider.parse_json_response(raw, list)
    if questions:
        save_questions(art_id, questions, config.GEMINI_MODEL)
        logger.info("Questions | id=%d | count=%d", art_id, len(questions))
        return questions
    return []

async def link_pyqs(article, tags=None, insights=None):
    art_id   = article["id"]
    title    = article.get("title","")
    topics   = (tags or {}).get("topics",[])
    concepts = (insights or {}).get("related_concepts",[])
    if not topics and not concepts: return []
    if (tags or {}).get("prelims_relevance",0) < 6 and (tags or {}).get("mains_relevance",0) < 6: return []
    prompt = pyq_linker_prompt(title, topics, concepts)
    raw, finish, latency = await ai_provider.call(SYS_PYQ, prompt, max_tokens=config.TOKENS_PYQ_LINK, temperature=0.1, task_name="pyq_link")
    log_ai_session(art_id,"pyq_link",config.GEMINI_MODEL,len(prompt),len(raw),finish,latency,success=bool(raw))
    pyqs = ai_provider.parse_json_response(raw, list)
    if pyqs:
        valid = [p for p in pyqs if p.get("pyq_question") and p.get("pyq_year")]
        if valid:
            save_pyq_connections(art_id, valid, config.GEMINI_MODEL)
            logger.info("PYQ links | id=%d | count=%d", art_id, len(valid))
            return valid
    return []
