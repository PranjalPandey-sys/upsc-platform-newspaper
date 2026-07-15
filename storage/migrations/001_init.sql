-- 001_init.sql — PostgreSQL schema (migration target from SQLite v1)
BEGIN;

CREATE TABLE IF NOT EXISTS sources (
    id                     SERIAL PRIMARY KEY,
    name                   TEXT        NOT NULL,
    rss_url                TEXT        NOT NULL UNIQUE,
    base_url               TEXT        DEFAULT \'\',
    active                 BOOLEAN     DEFAULT TRUE,
    fetch_frequency_hours  INTEGER     DEFAULT 24,
    upsc_relevance_tier    INTEGER     DEFAULT 2,
    created_at             TIMESTAMPTZ DEFAULT NOW(),
    last_fetched_at        TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS articles (
    id                SERIAL PRIMARY KEY,
    content_hash      TEXT        NOT NULL UNIQUE,
    source_id         INTEGER     NOT NULL REFERENCES sources(id),
    url               TEXT        NOT NULL,
    title             TEXT        NOT NULL,
    rss_summary       TEXT        DEFAULT \'\',
    full_text         TEXT        DEFAULT \'\',
    author            TEXT        DEFAULT \'\',
    published_at      TIMESTAMPTZ,
    fetched_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    extraction_status TEXT        DEFAULT \'pending\',
    analysis_status   TEXT        DEFAULT \'pending\',
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    search_vector     TSVECTOR
);

CREATE TABLE IF NOT EXISTS article_tags (
    id                   SERIAL PRIMARY KEY,
    article_id           INTEGER      NOT NULL UNIQUE REFERENCES articles(id) ON DELETE CASCADE,
    gs_papers            JSONB        DEFAULT \'[]\',
    syllabus_sections    JSONB        DEFAULT \'[]\',
    subject_tags         JSONB        DEFAULT \'[]\',
    prelims_relevance    SMALLINT     DEFAULT 0,
    mains_relevance      SMALLINT     DEFAULT 0,
    difficulty_prelims   TEXT         DEFAULT \'medium\',
    topics               JSONB        DEFAULT \'[]\',
    keywords             JSONB        DEFAULT \'[]\',
    is_current_affairs   BOOLEAN      DEFAULT TRUE,
    generated_at         TIMESTAMPTZ  DEFAULT NOW(),
    ai_model             TEXT         DEFAULT \'\'
);

CREATE TABLE IF NOT EXISTS article_summaries (
    id                SERIAL PRIMARY KEY,
    article_id        INTEGER      NOT NULL UNIQUE REFERENCES articles(id) ON DELETE CASCADE,
    short_summary     TEXT         DEFAULT \'\',
    detailed_summary  TEXT         DEFAULT \'\',
    upsc_significance TEXT         DEFAULT \'\',
    generated_at      TIMESTAMPTZ  DEFAULT NOW(),
    ai_model          TEXT         DEFAULT \'\'
);

CREATE TABLE IF NOT EXISTS article_insights (
    id                      SERIAL PRIMARY KEY,
    article_id              INTEGER      NOT NULL UNIQUE REFERENCES articles(id) ON DELETE CASCADE,
    background              TEXT         DEFAULT \'\',
    causes                  JSONB        DEFAULT \'[]\',
    consequences            JSONB        DEFAULT \'[]\',
    constitutional_articles JSONB        DEFAULT \'[]\',
    acts_and_laws           JSONB        DEFAULT \'[]\',
    committees_commissions  JSONB        DEFAULT \'[]\',
    government_schemes      JSONB        DEFAULT \'[]\',
    international_orgs      JSONB        DEFAULT \'[]\',
    related_concepts        JSONB        DEFAULT \'[]\',
    key_facts               JSONB        DEFAULT \'[]\',
    way_forward             TEXT         DEFAULT \'\',
    generated_at            TIMESTAMPTZ  DEFAULT NOW(),
    ai_model                TEXT         DEFAULT \'\'
);

CREATE TABLE IF NOT EXISTS practice_questions (
    id             SERIAL PRIMARY KEY,
    article_id     INTEGER      NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    question_type  TEXT         NOT NULL,
    question_text  TEXT         NOT NULL,
    options        JSONB        DEFAULT \'[]\',
    correct_answer TEXT         DEFAULT \'\',
    explanation    TEXT         DEFAULT \'\',
    marks          SMALLINT     DEFAULT 0,
    difficulty     TEXT         DEFAULT \'medium\',
    generated_at   TIMESTAMPTZ  DEFAULT NOW(),
    ai_model       TEXT         DEFAULT \'\'
);

CREATE TABLE IF NOT EXISTS pyq_connections (
    id                   SERIAL PRIMARY KEY,
    article_id           INTEGER      NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    pyq_year             SMALLINT,
    pyq_paper            TEXT         DEFAULT \'\',
    pyq_question         TEXT         NOT NULL,
    connection_type      TEXT         DEFAULT \'thematic\',
    connection_relevance TEXT         DEFAULT \'\',
    generated_at         TIMESTAMPTZ  DEFAULT NOW(),
    ai_model             TEXT         DEFAULT \'\'
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id                 SERIAL PRIMARY KEY,
    source_id          INTEGER      NOT NULL REFERENCES sources(id),
    started_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    finished_at        TIMESTAMPTZ,
    articles_fetched   INTEGER      DEFAULT 0,
    articles_new       INTEGER      DEFAULT 0,
    articles_duplicate INTEGER      DEFAULT 0,
    articles_failed    INTEGER      DEFAULT 0,
    status             TEXT         DEFAULT \'running\',
    error_message      TEXT         DEFAULT \'\'
);

CREATE TABLE IF NOT EXISTS ai_sessions (
    id             SERIAL PRIMARY KEY,
    article_id     INTEGER      REFERENCES articles(id) ON DELETE SET NULL,
    task_type      TEXT         NOT NULL,
    model          TEXT         NOT NULL,
    input_chars    INTEGER      DEFAULT 0,
    output_chars   INTEGER      DEFAULT 0,
    finish_reason  TEXT         DEFAULT \'\',
    latency_ms     INTEGER      DEFAULT 0,
    success        BOOLEAN      DEFAULT TRUE,
    error_message  TEXT         DEFAULT \'\',
    created_at     TIMESTAMPTZ  DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_articles_source    ON articles(source_id);
CREATE INDEX IF NOT EXISTS idx_articles_status    ON articles(analysis_status);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_tags_gs            ON article_tags USING GIN(gs_papers);
CREATE INDEX IF NOT EXISTS idx_tags_subjects      ON article_tags USING GIN(subject_tags);
CREATE INDEX IF NOT EXISTS idx_tags_prelims       ON article_tags(prelims_relevance DESC);
CREATE INDEX IF NOT EXISTS idx_ai_trunc           ON ai_sessions(finish_reason) WHERE finish_reason=\'length\';
CREATE INDEX IF NOT EXISTS idx_articles_fts       ON articles USING GIN(search_vector);

-- Full-text search trigger
CREATE OR REPLACE FUNCTION update_article_fts() RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector(\'english\', COALESCE(NEW.title,\'\')), \'A\') ||
        setweight(to_tsvector(\'english\', COALESCE(NEW.rss_summary,\'\')), \'B\') ||
        setweight(to_tsvector(\'english\', COALESCE(NEW.full_text,\'\')), \'C\');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_article_fts ON articles;
CREATE TRIGGER trg_article_fts
    BEFORE INSERT OR UPDATE OF title,rss_summary,full_text ON articles
    FOR EACH ROW EXECUTE FUNCTION update_article_fts();

COMMIT;
