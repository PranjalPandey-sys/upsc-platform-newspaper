"""api/router.py — All FastAPI Route Handlers."""
import json, logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from api.auth import require_api_key
from api.schemas import (
    ArticleDetail, ArticleListItem, DailyDigest, DigestArticle,
    HealthResponse, PaginatedArticles, PipelineResult, Question,
    SourceOut, Tags, Summary, Insights, PYQConnection,
)
from storage import database as db
from utils.helpers import today_ist_str

logger  = logging.getLogger(__name__)
router  = APIRouter(prefix="/api/v1")
AuthDep = Annotated[str, Depends(require_api_key)]

def _safe(row): return bool(row.get("id") and row.get("title") and row.get("url"))
def _jl(v): return json.loads(v) if isinstance(v, str) else (v or [])

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    try:
        s = db.get_stats()
        return HealthResponse(status="healthy", database="ok",
            articles_done=s["articles_done"], articles_pending=s["articles_pending"],
            ai_truncations=s["ai_truncations"], active_sources=s["active_sources"])
    except Exception:
        return HealthResponse(status="degraded", database="error",
            articles_done=0, articles_pending=0, ai_truncations=0, active_sources=0)

@router.get("/sources", response_model=list[SourceOut], tags=["Sources"])
async def list_sources(api_key: AuthDep):
    sources = db.get_active_sources()
    return [SourceOut(id=s["id"], name=s["name"], rss_url=s["rss_url"],
                      active=bool(s["active"]), upsc_relevance_tier=s["upsc_relevance_tier"],
                      last_fetched_at=s.get("last_fetched_at")) for s in sources]

@router.get("/articles", response_model=PaginatedArticles, tags=["Articles"])
async def list_articles(
    api_key: AuthDep,
    gs_paper:    str | None = Query(None),
    subject:     str | None = Query(None),
    date_from:   str | None = Query(None),
    min_prelims: int        = Query(0, ge=0, le=10),
    min_mains:   int        = Query(0, ge=0, le=10),
    source_id:   int | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    rows = db.get_articles_for_api(limit=limit, offset=offset, gs_paper=gs_paper,
        subject=subject, date_from=date_from, min_prelims=min_prelims,
        min_mains=min_mains, source_id=source_id)
    articles = []
    for row in rows:
        try:
            articles.append(ArticleListItem(**{k: row[k] for k in ArticleListItem.model_fields if k in row}))
        except Exception: pass
    return PaginatedArticles(total=len(articles), limit=limit, offset=offset, articles=articles)

@router.get("/articles/today", response_model=list[ArticleListItem], tags=["Articles"])
async def todays_articles(api_key: AuthDep, min_prelims: int = Query(5, ge=0, le=10)):
    rows = db.get_articles_for_api(limit=50, date_from=today_ist_str(), min_prelims=min_prelims)
    result = []
    for r in rows:
        if _safe(r):
            try: result.append(ArticleListItem(**{k: r[k] for k in ArticleListItem.model_fields if k in r}))
            except Exception: pass
    return result

@router.get("/articles/{article_id}", response_model=ArticleDetail, tags=["Articles"])
async def get_article(api_key: AuthDep, article_id: int):
    detail = db.get_full_article_detail(article_id)
    if not detail: raise HTTPException(status_code=404, detail=f"Article {article_id} not found")
    return _build_detail(detail)

@router.post("/articles/{article_id}/regenerate", response_model=PipelineResult, tags=["Admin"])
async def regenerate_article(api_key: AuthDep, article_id: int, bg: BackgroundTasks):
    article = db.get_article(article_id)
    if not article: raise HTTPException(status_code=404, detail=f"Article {article_id} not found")
    from services.pipeline import regenerate_article as _regen
    bg.add_task(_regen, article_id)
    return PipelineResult(status="queued", message=f"Regeneration queued for article {article_id}",
                          details={"article_id": article_id, "title": article.get("title","")})

@router.get("/search", response_model=list[ArticleListItem], tags=["Search"])
async def search_articles(api_key: AuthDep,
                          q: str = Query(..., min_length=2),
                          limit: int = Query(15, ge=1, le=50)):
    rows = db.search_articles(q, limit)
    result = []
    for r in rows:
        if _safe(r):
            try: result.append(ArticleListItem(**{k: r[k] for k in ArticleListItem.model_fields if k in r}))
            except Exception: pass
    return result

@router.get("/questions", response_model=list[Question], tags=["Questions"])
async def get_questions(
    api_key: AuthDep,
    q_type:    str       = Query("prelims"),
    subject:   str | None = Query(None),
    gs_paper:  str | None = Query(None),
    difficulty: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    params, wheres = [], ["1=1"]
    if q_type != "all": wheres.append("pq.question_type=?"); params.append(q_type)
    if difficulty:      wheres.append("pq.difficulty=?");    params.append(difficulty)
    if subject or gs_paper:
        sub = " AND t.subject_tags LIKE ?" if subject else ""
        gsp = " AND t.gs_papers LIKE ?" if gs_paper else ""
        wheres.append(f"EXISTS (SELECT 1 FROM article_tags t WHERE t.article_id=pq.article_id{sub}{gsp})")
        if subject:   params.append(f"%{subject}%")
        if gs_paper:  params.append(f"%{gs_paper}%")
    params.append(limit)
    from storage.database import get_db
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM practice_questions pq WHERE {' AND '.join(wheres)} ORDER BY RANDOM() LIMIT ?",
            params
        ).fetchall()
    result = []
    for r in rows:
        try: result.append(Question(**{k: dict(r)[k] for k in Question.model_fields if k in dict(r)}))
        except Exception: pass
    return result

@router.get("/digest/daily", response_model=DailyDigest, tags=["Digest"])
async def daily_digest(
    api_key: AuthDep,
    date: str | None = Query(None),
    min_prelims: int = Query(5, ge=0, le=10),
    limit: int = Query(10, ge=1, le=30),
):
    target = date or today_ist_str()
    rows   = db.get_articles_for_api(limit=limit*2, date_from=target, min_prelims=min_prelims)
    rows.sort(key=lambda r: r.get("prelims_relevance", 0), reverse=True)
    items = []
    from storage.database import get_db
    for row in rows[:limit]:
        if not _safe(row): continue
        art_id = row["id"]
        key_facts, schemes, prelims_q = [], [], ""
        try:
            with get_db() as conn:
                ins = conn.execute("SELECT key_facts,government_schemes FROM article_insights WHERE article_id=?", (art_id,)).fetchone()
                if ins:
                    key_facts = _jl(ins["key_facts"])[:4]
                    schemes   = _jl(ins["government_schemes"])[:3]
                q = conn.execute("SELECT question_text FROM practice_questions WHERE article_id=? AND question_type=\'prelims\' LIMIT 1", (art_id,)).fetchone()
                if q: prelims_q = q["question_text"]
        except Exception: pass
        items.append(DigestArticle(
            id=art_id, title=row.get("title",""), url=row.get("url",""),
            source_name=row.get("source_name",""),
            gs_papers=_jl(row.get("gs_papers","[]")),
            prelims_relevance=row.get("prelims_relevance",0),
            mains_relevance=row.get("mains_relevance",0),
            short_summary=row.get("short_summary",""),
            upsc_significance=row.get("upsc_significance",""),
            key_facts=key_facts, government_schemes=schemes,
            prelims_question=prelims_q,
        ))
    return DailyDigest(date=target, total_articles=len(items), articles=items)

@router.post("/admin/run/ingestion", response_model=PipelineResult, tags=["Admin"])
async def trigger_ingestion(api_key: AuthDep, bg: BackgroundTasks):
    from scheduler.jobs import job_ingestion
    bg.add_task(job_ingestion)
    return PipelineResult(status="started", message="Ingestion started in background")

@router.post("/admin/run/extraction", response_model=PipelineResult, tags=["Admin"])
async def trigger_extraction(api_key: AuthDep, bg: BackgroundTasks):
    from scheduler.jobs import job_extraction
    bg.add_task(job_extraction)
    return PipelineResult(status="started", message="Extraction started in background")

@router.post("/admin/run/analysis", response_model=PipelineResult, tags=["Admin"])
async def trigger_analysis(api_key: AuthDep, bg: BackgroundTasks):
    from scheduler.jobs import job_analysis
    bg.add_task(job_analysis)
    return PipelineResult(status="started", message="AI analysis started in background")

@router.post("/admin/run/full", response_model=PipelineResult, tags=["Admin"])
async def trigger_full(api_key: AuthDep, bg: BackgroundTasks):
    from scheduler.jobs import job_full_daily_run
    bg.add_task(job_full_daily_run)
    return PipelineResult(status="started", message="Full daily pipeline started in background")

@router.get("/admin/stats", tags=["Admin"])
async def get_stats(api_key: AuthDep):
    stats = db.get_stats()
    from storage.database import get_db
    with get_db() as conn:
        reasons = [dict(r) for r in conn.execute(
            "SELECT task_type,finish_reason,COUNT(*) as cnt FROM ai_sessions GROUP BY task_type,finish_reason ORDER BY cnt DESC LIMIT 20"
        ).fetchall()]
        last_runs = [dict(r) for r in conn.execute(
            "SELECT s.name,r.status,r.articles_new,r.finished_at FROM ingestion_runs r JOIN sources s ON r.source_id=s.id ORDER BY r.started_at DESC LIMIT 5"
        ).fetchall()]
    return {"pipeline_stats": stats, "ai_finish_reasons": reasons, "last_ingestion_runs": last_runs}

def _build_detail(detail: dict) -> ArticleDetail:
    def _m(cls, data):
        if not data: return None
        try: return cls(**{k: data[k] for k in cls.model_fields if k in data})
        except Exception: return None
    tags_obj     = _m(Tags,     detail.get("tags") or {})
    summary_obj  = _m(Summary,  detail.get("summaries") or {})
    insights_obj = _m(Insights, detail.get("insights") or {})
    questions = []
    for q in detail.get("questions", []):
        try: questions.append(Question(**{k: q[k] for k in Question.model_fields if k in q}))
        except Exception: pass
    pyqs = []
    for p in detail.get("pyq_connections", []):
        try: pyqs.append(PYQConnection(**{k: p[k] for k in PYQConnection.model_fields if k in p}))
        except Exception: pass
    return ArticleDetail(
        id=detail["id"], title=detail.get("title",""), url=detail.get("url",""),
        source_name=detail.get("source_name",""), author=detail.get("author",""),
        published_at=detail.get("published_at",""), rss_summary=detail.get("rss_summary",""),
        full_text=detail.get("full_text","")[:800],
        analysis_status=detail.get("analysis_status",""),
        tags=tags_obj, summaries=summary_obj, insights=insights_obj,
        questions=questions, pyq_connections=pyqs,
    )
