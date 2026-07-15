"""main.py — Newspaper Intelligence Engine Entry Point."""
import logging
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from utils.logger import setup_logging
setup_logging()

import config
from storage.database import init_db
from scheduler.jobs import register_jobs
from api.router import router

logger = logging.getLogger(__name__)
_scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    logger.info("=" * 55)
    logger.info("UPSC Newspaper Intelligence Engine — Starting")
    logger.info("=" * 55)
    init_db()
    _scheduler = AsyncIOScheduler(timezone="UTC")
    register_jobs(_scheduler)
    _scheduler.start()
    logger.info("Scheduler started | %d jobs", len(_scheduler.get_jobs()))
    logger.info("DB:    %s", config.DB_PATH)
    logger.info("Model: %s | reasoning=%s", config.GEMINI_MODEL, config.GEMINI_REASONING)
    logger.info("Keys:  %d configured", len(config.API_KEYS))
    logger.info("=" * 55)
    logger.info("Engine is live!")
    yield
    logger.info("Shutting down...")
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)

app = FastAPI(
    title="UPSC Newspaper Intelligence Engine",
    description="AI-powered news analysis for UPSC preparation. Ingests RSS feeds daily, classifies by UPSC syllabus, generates summaries, insights, and practice questions.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=False,
    allow_methods=["GET","POST"],
    allow_headers=["X-API-Key","Content-Type"],
)

app.include_router(router)

@app.get("/", tags=["System"])
async def root():
    return {"service": "UPSC Newspaper Intelligence Engine", "version": "1.0.0",
            "docs": "/docs", "health": "/api/v1/health"}

@app.get("/ping", tags=["System"])
async def ping():
    return "pong"
