"""storage/database.py — SQLite Database Layer."""
import json, logging, sqlite3
from contextlib import contextmanager
import config
from utils.helpers import iso_now

logger = logging.getLogger(__name__)

def _get_conn():
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

@contextmanager
def get_db():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, rss_url TEXT NOT NULL UNIQUE,
    base_url TEXT DEFAULT "", active INTEGER DEFAULT 1,
    fetch_frequency_hours INTEGER DEFAULT 24,
    upsc_relevance_tier INTEGER DEFAULT 2,
    created_at TEXT NOT NULL, last_fetched_at TEXT DEFAULT ""
);
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT NOT NULL UNIQUE,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    url TEXT NOT NULL, title TEXT NOT NULL,
    rss_summary TEXT DEFAULT "", full_text TEXT DEFAULT "",
    author TEXT DEFAULT "", published_at TEXT DEFAULT "",
    fetched_at TEXT NOT NULL,
    extraction_status TEXT DEFAULT "pending",
    analysis_status TEXT DEFAULT "pending",
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS article_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL UNIQUE REFERENCES articles(id) ON DELETE CASCADE,
    gs_papers TEXT DEFAULT "[]", syllabus_sections TEXT DEFAULT "[]",
    subject_tags TEXT DEFAULT "[]", prelims_relevance INTEGER DEFAULT 0,
    mains_relevance INTEGER DEFAULT 0, difficulty_prelims TEXT DEFAULT "medium",
    topics TEXT DEFAULT "[]", keywords TEXT DEFAULT "[]",
    is_current_affairs INTEGER DEFAULT 1,
    generated_at TEXT NOT NULL, ai_model TEXT DEFAULT ""
);
CREATE TABLE IF NOT EXISTS article_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL UNIQUE REFERENCES articles(id) ON DELETE CASCADE,
    short_summary TEXT DEFAULT "", detailed_summary TEXT DEFAULT "",
    upsc_significance TEXT DEFAULT "",
    generated_at TEXT NOT NULL, ai_model TEXT DEFAULT ""
);
CREATE TABLE IF NOT EXISTS article_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL UNIQUE REFERENCES articles(id) ON DELETE CASCADE,
    background TEXT DEFAULT "",
    causes TEXT DEFAULT "[]", consequences TEXT DEFAULT "[]",
    constitutional_articles TEXT DEFAULT "[]", acts_and_laws TEXT DEFAULT "[]",
    committees_commissions TEXT DEFAULT "[]", government_schemes TEXT DEFAULT "[]",
    international_orgs TEXT DEFAULT "[]", related_concepts TEXT DEFAULT "[]",
    key_facts TEXT DEFAULT "[]", way_forward TEXT DEFAULT "",
    generated_at TEXT NOT NULL, ai_model TEXT DEFAULT ""
);
CREATE TABLE IF NOT EXISTS practice_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    question_type TEXT NOT NULL, question_text TEXT NOT NULL,
    options TEXT DEFAULT "[]", correct_answer TEXT DEFAULT "",
    explanation TEXT DEFAULT "", marks INTEGER DEFAULT 0,
    difficulty TEXT DEFAULT "medium",
    generated_at TEXT NOT NULL, ai_model TEXT DEFAULT ""
);
CREATE TABLE IF NOT EXISTS pyq_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    pyq_year INTEGER, pyq_paper TEXT DEFAULT "",
    pyq_question TEXT NOT NULL, connection_type TEXT DEFAULT "thematic",
    connection_relevance TEXT DEFAULT "",
    generated_at TEXT NOT NULL, ai_model TEXT DEFAULT ""
);
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    started_at TEXT NOT NULL, finished_at TEXT DEFAULT "",
    articles_fetched INTEGER DEFAULT 0, articles_new INTEGER DEFAULT 0,
    articles_duplicate INTEGER DEFAULT 0, articles_failed INTEGER DEFAULT 0,
    status TEXT DEFAULT "running", error_message TEXT DEFAULT ""
);
CREATE TABLE IF NOT EXISTS ai_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER REFERENCES articles(id),
    task_type TEXT NOT NULL, model TEXT NOT NULL,
    input_chars INTEGER DEFAULT 0, output_chars INTEGER DEFAULT 0,
    finish_reason TEXT DEFAULT "", latency_ms INTEGER DEFAULT 0,
    success INTEGER DEFAULT 1, error_message TEXT DEFAULT "",
    created_at TEXT NOT NULL
);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_articles_source    ON articles(source_id);
CREATE INDEX IF NOT EXISTS idx_articles_status    ON articles(analysis_status);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_hash      ON articles(content_hash);
CREATE INDEX IF NOT EXISTS idx_tags_prelims       ON article_tags(prelims_relevance DESC);
CREATE INDEX IF NOT EXISTS idx_tags_mains         ON article_tags(mains_relevance DESC);
CREATE INDEX IF NOT EXISTS idx_questions_type     ON practice_questions(question_type);
CREATE INDEX IF NOT EXISTS idx_ai_task            ON ai_sessions(task_type, created_at);
"""

DEFAULT_SOURCES = [
    {"name":"PIB - Press Information Bureau","rss_url":"https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3","base_url":"https://pib.gov.in","upsc_relevance_tier":1,"fetch_frequency_hours":6},
    {"name":"PIB - Ministry of Finance","rss_url":"https://pib.gov.in/RssMain.aspx?ModId=3&Lang=1&Regid=3","base_url":"https://pib.gov.in","upsc_relevance_tier":1,"fetch_frequency_hours":6},
    {"name":"PIB - Ministry of External Affairs","rss_url":"https://pib.gov.in/RssMain.aspx?ModId=46&Lang=1&Regid=3","base_url":"https://pib.gov.in","upsc_relevance_tier":1,"fetch_frequency_hours":12},
    {"name":"The Hindu - National","rss_url":"https://www.thehindu.com/news/national/feeder/default.rss","base_url":"https://www.thehindu.com","upsc_relevance_tier":1,"fetch_frequency_hours":12},
    {"name":"The Hindu - Economy","rss_url":"https://www.thehindu.com/business/Economy/feeder/default.rss","base_url":"https://www.thehindu.com","upsc_relevance_tier":1,"fetch_frequency_hours":12},
    {"name":"The Hindu - International","rss_url":"https://www.thehindu.com/news/international/feeder/default.rss","base_url":"https://www.thehindu.com","upsc_relevance_tier":1,"fetch_frequency_hours":12},
    {"name":"The Hindu - Science & Tech","rss_url":"https://www.thehindu.com/sci-tech/feeder/default.rss","base_url":"https://www.thehindu.com","upsc_relevance_tier":2,"fetch_frequency_hours":24},
    {"name":"Indian Express - India","rss_url":"https://indianexpress.com/section/india/feed/","base_url":"https://indianexpress.com","upsc_relevance_tier":1,"fetch_frequency_hours":12},
    {"name":"Indian Express - Economy","rss_url":"https://indianexpress.com/section/business/economy/feed/","base_url":"https://indianexpress.com","upsc_relevance_tier":1,"fetch_frequency_hours":12},
    {"name":"Down To Earth - Environment","rss_url":"https://www.downtoearth.org.in/rss/latest-news","base_url":"https://www.downtoearth.org.in","upsc_relevance_tier":1,"fetch_frequency_hours":24},
    {"name":"MEA - Press Releases","rss_url":"https://www.mea.gov.in/rss/press-releases.xml","base_url":"https://www.mea.gov.in","upsc_relevance_tier":1,"fetch_frequency_hours":12},
    {"name":"Rajya Sabha TV","rss_url":"https://www.rstv.nic.in/rss.php","base_url":"https://www.rstv.nic.in","upsc_relevance_tier":2,"fetch_frequency_hours":24},
]

def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)
        conn.executescript(INDEXES)
        now = iso_now()
        for s in DEFAULT_SOURCES:
            conn.execute(
                "INSERT OR IGNORE INTO sources(name,rss_url,base_url,active,fetch_frequency_hours,upsc_relevance_tier,created_at) VALUES(?,?,?,1,?,?,?)",
                (s["name"],s["rss_url"],s["base_url"],s["fetch_frequency_hours"],s["upsc_relevance_tier"],now)
            )
    logger.info("DB initialised | path=%s", config.DB_PATH)

def get_active_sources():
    with get_db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM sources WHERE active=1 ORDER BY upsc_relevance_tier,id").fetchall()]

def update_source_fetched(source_id):
    with get_db() as conn:
        conn.execute("UPDATE sources SET last_fetched_at=? WHERE id=?", (iso_now(), source_id))

def article_exists(content_hash):
    with get_db() as conn:
        return conn.execute("SELECT 1 FROM articles WHERE content_hash=?", (content_hash,)).fetchone() is not None

def insert_article(data):
    try:
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO articles(content_hash,source_id,url,title,rss_summary,author,published_at,fetched_at,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (data["content_hash"],data["source_id"],data["url"],data["title"],
                 data.get("rss_summary",""),data.get("author",""),data.get("published_at",""),
                 iso_now(),iso_now())
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None

def get_article(article_id):
    with get_db() as conn:
        r = conn.execute("SELECT * FROM articles WHERE id=?", (article_id,)).fetchone()
        return dict(r) if r else None

def get_pending_extraction(limit=20):
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM articles WHERE extraction_status=\'pending\' ORDER BY created_at ASC LIMIT ?", (limit,)
        ).fetchall()]

def get_pending_analysis(limit=10):
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM articles WHERE analysis_status=\'pending\' AND extraction_status IN (\'done\',\'skipped\') ORDER BY published_at DESC LIMIT ?", (limit,)
        ).fetchall()]

def update_article_extraction(article_id, full_text, status):
    with get_db() as conn:
        conn.execute("UPDATE articles SET full_text=?,extraction_status=? WHERE id=?", (full_text,status,article_id))

def update_article_analysis_status(article_id, status):
    with get_db() as conn:
        conn.execute("UPDATE articles SET analysis_status=? WHERE id=?", (status,article_id))

def get_articles_for_api(limit=20, offset=0, gs_paper=None, subject=None,
                         date_from=None, min_prelims=0, min_mains=0, source_id=None):
    params, wheres = [], ["a.analysis_status=\'done\'"]
    if gs_paper: wheres.append("t.gs_papers LIKE ?"); params.append(f"%{gs_paper}%")
    if subject: wheres.append("(t.subject_tags LIKE ? OR t.syllabus_sections LIKE ?)"); params.extend([f"%{subject}%"]*2)
    if date_from: wheres.append("a.published_at >= ?"); params.append(date_from)
    if min_prelims > 0: wheres.append("t.prelims_relevance >= ?"); params.append(min_prelims)
    if min_mains > 0: wheres.append("t.mains_relevance >= ?"); params.append(min_mains)
    if source_id: wheres.append("a.source_id=?"); params.append(source_id)
    params.extend([limit, offset])
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT a.*,s.name AS source_name,t.gs_papers,t.subject_tags,t.prelims_relevance,t.mains_relevance,sm.short_summary,sm.upsc_significance FROM articles a LEFT JOIN sources s ON a.source_id=s.id LEFT JOIN article_tags t ON a.id=t.article_id LEFT JOIN article_summaries sm ON a.id=sm.article_id WHERE {' AND '.join(wheres)} ORDER BY a.published_at DESC LIMIT ? OFFSET ?",
            params
        ).fetchall()
        return [dict(r) for r in rows]

def get_full_article_detail(article_id):
    with get_db() as conn:
        a = conn.execute("SELECT * FROM articles WHERE id=?", (article_id,)).fetchone()
        if not a: return None
        result = dict(a)
        src = conn.execute("SELECT name FROM sources WHERE id=?", (a["source_id"],)).fetchone()
        result["source_name"] = src["name"] if src else ""
        for table, key in [("article_tags","tags"),("article_summaries","summaries"),("article_insights","insights")]:
            row = conn.execute(f"SELECT * FROM {table} WHERE article_id=?", (article_id,)).fetchone()
            result[key] = dict(row) if row else {}
        result["questions"] = [dict(q) for q in conn.execute("SELECT * FROM practice_questions WHERE article_id=? ORDER BY question_type,id", (article_id,)).fetchall()]
        result["pyq_connections"] = [dict(p) for p in conn.execute("SELECT * FROM pyq_connections WHERE article_id=?", (article_id,)).fetchall()]
        return result

def search_articles(query, limit=20):
    p = f"%{query}%"
    with get_db() as conn:
        rows = conn.execute(
            "SELECT a.id,a.title,a.url,a.published_at,s.name AS source_name,t.gs_papers,t.subject_tags,t.prelims_relevance,sm.short_summary FROM articles a LEFT JOIN sources s ON a.source_id=s.id LEFT JOIN article_tags t ON a.id=t.article_id LEFT JOIN article_summaries sm ON a.id=sm.article_id WHERE a.analysis_status=\'done\' AND (a.title LIKE ? OR sm.short_summary LIKE ? OR t.subject_tags LIKE ? OR t.topics LIKE ?) ORDER BY a.published_at DESC LIMIT ?",
            (p,p,p,p,limit)
        ).fetchall()
        return [dict(r) for r in rows]

def count_articles(status="done"):
    with get_db() as conn:
        r = conn.execute("SELECT COUNT(*) FROM articles WHERE analysis_status=?", (status,)).fetchone()
        return r[0] if r else 0

def save_tags(article_id, data, model):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO article_tags(article_id,gs_papers,syllabus_sections,subject_tags,prelims_relevance,mains_relevance,difficulty_prelims,topics,keywords,is_current_affairs,generated_at,ai_model) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (article_id,
             json.dumps(data.get("gs_papers",[]),ensure_ascii=False),
             json.dumps(data.get("syllabus_sections",[]),ensure_ascii=False),
             json.dumps(data.get("subject_tags",[]),ensure_ascii=False),
             int(data.get("prelims_relevance",0)), int(data.get("mains_relevance",0)),
             data.get("difficulty_prelims","medium"),
             json.dumps(data.get("topics",[]),ensure_ascii=False),
             json.dumps(data.get("keywords",[]),ensure_ascii=False),
             1 if data.get("is_current_affairs",True) else 0,
             iso_now(), model)
        )

def save_summary(article_id, data, model):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO article_summaries(article_id,short_summary,detailed_summary,upsc_significance,generated_at,ai_model) VALUES(?,?,?,?,?,?)",
            (article_id,data.get("short_summary",""),data.get("detailed_summary",""),data.get("upsc_significance",""),iso_now(),model)
        )

def save_insights(article_id, data, model):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO article_insights(article_id,background,causes,consequences,constitutional_articles,acts_and_laws,committees_commissions,government_schemes,international_orgs,related_concepts,key_facts,way_forward,generated_at,ai_model) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (article_id, data.get("background",""),
             json.dumps(data.get("causes",[]),ensure_ascii=False),
             json.dumps(data.get("consequences",[]),ensure_ascii=False),
             json.dumps(data.get("constitutional_articles",[]),ensure_ascii=False),
             json.dumps(data.get("acts_and_laws",[]),ensure_ascii=False),
             json.dumps(data.get("committees_commissions",[]),ensure_ascii=False),
             json.dumps(data.get("government_schemes",[]),ensure_ascii=False),
             json.dumps(data.get("international_orgs",[]),ensure_ascii=False),
             json.dumps(data.get("related_concepts",[]),ensure_ascii=False),
             json.dumps(data.get("key_facts",[]),ensure_ascii=False),
             data.get("way_forward",""), iso_now(), model)
        )

def save_questions(article_id, questions, model):
    now = iso_now()
    with get_db() as conn:
        for q in questions:
            conn.execute(
                "INSERT INTO practice_questions(article_id,question_type,question_text,options,correct_answer,explanation,marks,difficulty,generated_at,ai_model) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (article_id, q.get("question_type","prelims"), q.get("question_text",""),
                 json.dumps(q.get("options",[]),ensure_ascii=False),
                 q.get("correct_answer",""), q.get("explanation",""),
                 int(q.get("marks",0)), q.get("difficulty","medium"), now, model)
            )

def save_pyq_connections(article_id, pyqs, model):
    now = iso_now()
    with get_db() as conn:
        for p in pyqs:
            conn.execute(
                "INSERT INTO pyq_connections(article_id,pyq_year,pyq_paper,pyq_question,connection_type,connection_relevance,generated_at,ai_model) VALUES(?,?,?,?,?,?,?,?)",
                (article_id, int(p.get("pyq_year",0)), p.get("pyq_paper",""),
                 p.get("pyq_question",""), p.get("connection_type","thematic"),
                 p.get("connection_relevance",""), now, model)
            )

def log_ai_session(article_id, task_type, model, input_chars, output_chars,
                   finish_reason, latency_ms, success=True, error_message=""):
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO ai_sessions(article_id,task_type,model,input_chars,output_chars,finish_reason,latency_ms,success,error_message,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (article_id,task_type,model,input_chars,output_chars,finish_reason,latency_ms,1 if success else 0,error_message,iso_now())
            )
    except Exception:
        pass

def clear_ai_analysis(article_id):
    with get_db() as conn:
        for t in ["article_tags","article_summaries","article_insights","practice_questions","pyq_connections"]:
            conn.execute(f"DELETE FROM {t} WHERE article_id=?", (article_id,))
        conn.execute("UPDATE articles SET analysis_status=\'pending\' WHERE id=?", (article_id,))

def start_ingestion_run(source_id):
    with get_db() as conn:
        cur = conn.execute("INSERT INTO ingestion_runs(source_id,started_at,status) VALUES(?,?,\'running\')", (source_id, iso_now()))
        return cur.lastrowid

def finish_ingestion_run(run_id, fetched, new, duplicate, failed, status, error=""):
    with get_db() as conn:
        conn.execute("UPDATE ingestion_runs SET finished_at=?,articles_fetched=?,articles_new=?,articles_duplicate=?,articles_failed=?,status=?,error_message=? WHERE id=?",
                     (iso_now(),fetched,new,duplicate,failed,status,error,run_id))

def get_stats():
    with get_db() as conn:
        return {
            "articles_total":   conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0],
            "articles_done":    conn.execute("SELECT COUNT(*) FROM articles WHERE analysis_status=\'done\'").fetchone()[0],
            "articles_pending": conn.execute("SELECT COUNT(*) FROM articles WHERE analysis_status=\'pending\'").fetchone()[0],
            "articles_failed":  conn.execute("SELECT COUNT(*) FROM articles WHERE analysis_status=\'failed\'").fetchone()[0],
            "questions_total":  conn.execute("SELECT COUNT(*) FROM practice_questions").fetchone()[0],
            "active_sources":   conn.execute("SELECT COUNT(*) FROM sources WHERE active=1").fetchone()[0],
            "ai_truncations":   conn.execute("SELECT COUNT(*) FROM ai_sessions WHERE finish_reason=\'length\'").fetchone()[0],
        }
