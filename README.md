# 📰 UPSC Newspaper Intelligence Engine

An AI-powered backend service that transforms daily news into structured UPSC study material. Runs independently — integrates with the main Telegram bot via a clean REST API.

---

## What it does

Every day, automatically:
1. **Fetches** articles from 12 trusted RSS feeds (PIB, The Hindu, Indian Express, MEA, Down To Earth…)
2. **Extracts** full article text where publicly available
3. **Classifies** each article against the UPSC syllabus (GS1/GS2/GS3/GS4, specific sections)
4. **Summarises** in two modes: short (3-4 sentences for mobile) and detailed (comprehensive)
5. **Extracts structured insights**: background, causes, consequences, constitutional articles, schemes, committees, international organisations, related concepts, key facts
6. **Generates practice questions**: 2 Prelims MCQs + 2 Mains questions per article
7. **Links to previous year questions** where confident connections exist

---

## Architecture

```
RSS Feeds (12 sources)
        ↓
  Ingestion Layer          06:30 IST daily
  (rss_fetcher.py)
        ↓
  Content Extraction       07:30 IST daily
  (content_extractor.py)
        ↓
  AI Analysis Pipeline     08:30 IST daily
  ┌─────────────────────┐
  │ 1. UPSC Tagger      │ → article_tags
  │ 2. Summariser       │ → article_summaries
  │ 3. Insight Extractor│ → article_insights
  │ 4. Question Gen     │ → practice_questions
  │ 5. PYQ Linker       │ → pyq_connections
  └─────────────────────┘
        ↓
  SQLite Database (v1)
  PostgreSQL ready (see storage/migrations/001_init.sql)
        ↓
  FastAPI REST API
  (Telegram bot integrates here)
```

---

## Folder Structure

```
newspaper-engine/
├── main.py                    # FastAPI app + lifespan startup
├── config.py                  # All settings (env vars)
├── requirements.txt
├── render.yaml
│
├── ingestion/
│   ├── rss_fetcher.py         # Parse RSS feeds → RawArticle objects
│   └── content_extractor.py  # Extract full text via trafilatura
│
├── analysis/
│   ├── prompts.py             # All AI prompts (UPSC syllabus-aware)
│   ├── upsc_tagger.py         # Stage 1: classify by GS paper + syllabus
│   ├── summarizer.py          # Stage 2: short + detailed summaries
│   ├── insight_extractor.py   # Stage 3: structured UPSC insights
│   └── question_generator.py  # Stage 4+5: MCQs, Mains Qs, PYQ links
│
├── storage/
│   ├── database.py            # SQLite WAL schema + all query functions
│   └── migrations/
│       └── 001_init.sql       # PostgreSQL migration (for production scale)
│
├── api/
│   ├── auth.py                # X-API-Key header authentication
│   ├── schemas.py             # Pydantic request/response models
│   └── router.py              # All FastAPI route handlers
│
├── scheduler/
│   └── jobs.py                # APScheduler job definitions
│
├── services/
│   ├── ai_provider.py         # Gemini wrapper (reasoning_effort fix included)
│   ├── pipeline.py            # Orchestrates ingestion + analysis
│   └── backup.py              # GitHub DB backup
│
└── utils/
    ├── logger.py
    └── helpers.py
```

---

## Quick Start

```bash
git clone https://github.com/PranjalPandey-sys/upsc-platform-newspaper.git
cd upsc-platform-newspaper

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: set GEMINI_API_KEY and API_KEYS

uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for the interactive API explorer.

To manually run the full pipeline:
```bash
curl -X POST http://localhost:8000/api/v1/admin/run/full \
  -H "X-API-Key: your_key_here"
```

---

## Deploy on Render

1. Push repo to GitHub
2. Create a **Web Service** on Render
3. Runtime: **Python 3.11.9**
4. Build: `pip install -r requirements.txt`
5. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add **Persistent Disk** at `/data` (1 GB) for the SQLite database
7. Set environment variables: `GEMINI_API_KEY`, `API_KEYS`
8. Add UptimeRobot monitor: `https://your-app.onrender.com/ping` (5-minute interval)

---

## Telegram Bot Integration

In the Telegram bot (`config.py`), add:
```python
NEWSPAPER_API_URL = os.environ.get("NEWSPAPER_API_URL", "")
NEWSPAPER_API_KEY = os.environ.get("NEWSPAPER_API_KEY", "")
```

Key endpoints the bot will call:

| Bot Feature | Engine Endpoint |
|---|---|
| Morning CA push | `GET /api/v1/digest/daily` |
| CA section browsing | `GET /api/v1/articles?gs_paper=GS2` |
| Full article deep-read | `GET /api/v1/articles/{id}` |
| AI Planner CA search | `GET /api/v1/search?q=RBI+rate` |
| Mock test questions | `GET /api/v1/questions?q_type=prelims` |

---

## AI Quality Notes

**`reasoning_effort="none"`** is set on every Gemini call. Without this, gemini-2.5-flash burns half its token budget on silent thinking before emitting visible text, causing truncation. This single setting is responsible for answer completeness.

**Regeneration**: If the AI model improves, any article can be reprocessed:
```
POST /api/v1/articles/{id}/regenerate
```
Raw article text is preserved — only the AI-generated analysis is cleared and re-run.

**Hallucination note**: PYQ linking is set to low temperature (0.1) and explicitly instructs the model to return `[]` if not confident. This is the highest hallucination risk in the pipeline — treat PYQ connections as "suggested, not verified" until a ground-truth PYQ database is built.

---

## Database

SQLite (WAL mode) for v1. The schema is designed for zero-friction PostgreSQL migration — see `storage/migrations/001_init.sql` which includes JSONB columns, GIN indexes, and a full-text search trigger ready to activate.

**Regeneration-safe design**: Raw article data and AI analysis are in separate tables. Any AI table can be cleared and re-generated without re-fetching articles.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `API_KEYS` | ✅ | Comma-separated keys for bot auth |
| `GITHUB_TOKEN` | Optional | For daily DB backup |
| `GITHUB_REPO` | Optional | e.g. `username/backup-repo` |
| `DEBUG` | Optional | `true` for verbose logging |
