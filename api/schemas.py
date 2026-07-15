"""api/schemas.py — Pydantic Request/Response Schemas."""
import json
from typing import Any
from pydantic import BaseModel, field_validator

def _jlist(v) -> list:
    if isinstance(v, list): return v
    if isinstance(v, str):
        try: return json.loads(v)
        except: return []
    return []

class SourceOut(BaseModel):
    id: int; name: str; rss_url: str
    active: bool; upsc_relevance_tier: int
    last_fetched_at: str | None = None

class ArticleListItem(BaseModel):
    id: int; title: str; url: str
    source_name: str = ""; published_at: str = ""
    gs_papers: list[str] = []; subject_tags: list[str] = []
    prelims_relevance: int = 0; mains_relevance: int = 0
    short_summary: str = ""; upsc_significance: str = ""

    @field_validator("gs_papers","subject_tags", mode="before")
    @classmethod
    def pl(cls, v): return _jlist(v)

class Tags(BaseModel):
    gs_papers: list[str] = []; syllabus_sections: list[str] = []
    subject_tags: list[str] = []; prelims_relevance: int = 0
    mains_relevance: int = 0; difficulty_prelims: str = "medium"
    topics: list[str] = []; keywords: list[str] = []

    @field_validator("gs_papers","syllabus_sections","subject_tags","topics","keywords", mode="before")
    @classmethod
    def pl(cls, v): return _jlist(v)

class Summary(BaseModel):
    short_summary: str = ""; detailed_summary: str = ""; upsc_significance: str = ""

class Insights(BaseModel):
    background: str = ""; causes: list[str] = []; consequences: list[str] = []
    constitutional_articles: list[str] = []; acts_and_laws: list[str] = []
    committees_commissions: list[str] = []; government_schemes: list[str] = []
    international_orgs: list[str] = []; related_concepts: list[str] = []
    key_facts: list[str] = []; way_forward: str = ""

    @field_validator("causes","consequences","constitutional_articles","acts_and_laws",
                     "committees_commissions","government_schemes","international_orgs",
                     "related_concepts","key_facts", mode="before")
    @classmethod
    def pl(cls, v): return _jlist(v)

class Question(BaseModel):
    id: int; question_type: str = "prelims"; question_text: str
    options: list[str] = []; correct_answer: str = ""
    explanation: str = ""; marks: int = 0; difficulty: str = "medium"

    @field_validator("options", mode="before")
    @classmethod
    def pl(cls, v): return _jlist(v)

class PYQConnection(BaseModel):
    pyq_year: int = 0; pyq_paper: str = ""; pyq_question: str
    connection_type: str = "thematic"; connection_relevance: str = ""

class ArticleDetail(BaseModel):
    id: int; title: str; url: str; source_name: str = ""
    author: str = ""; published_at: str = ""; rss_summary: str = ""
    full_text: str = ""; analysis_status: str = ""
    tags: Tags | None = None; summaries: Summary | None = None
    insights: Insights | None = None
    questions: list[Question] = []; pyq_connections: list[PYQConnection] = []

class DigestArticle(BaseModel):
    id: int; title: str; url: str; source_name: str = ""
    gs_papers: list[str] = []; prelims_relevance: int = 0; mains_relevance: int = 0
    short_summary: str = ""; upsc_significance: str = ""
    key_facts: list[str] = []; government_schemes: list[str] = []
    prelims_question: str = ""

    @field_validator("gs_papers","key_facts","government_schemes", mode="before")
    @classmethod
    def pl(cls, v): return _jlist(v)

class DailyDigest(BaseModel):
    date: str; total_articles: int; articles: list[DigestArticle]

class PaginatedArticles(BaseModel):
    total: int; limit: int; offset: int; articles: list[ArticleListItem]

class PipelineResult(BaseModel):
    status: str; message: str; details: dict[str, Any] = {}

class HealthResponse(BaseModel):
    status: str; database: str
    articles_done: int; articles_pending: int
    ai_truncations: int; active_sources: int
