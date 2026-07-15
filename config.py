"""config.py — Newspaper Intelligence Engine Configuration."""
import os, pathlib, logging

BASE_DIR  = pathlib.Path(__file__).parent
LOGS_DIR  = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

_DATA_DIR = pathlib.Path("/data") if pathlib.Path("/data").exists() else BASE_DIR / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH: str = str(_DATA_DIR / "newspaper.db")

GEMINI_API_KEY:        str = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL:          str = "gemini-2.5-flash"
GEMINI_BASE_URL:       str = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_REASONING:      str = "none"
GEMINI_TIMEOUT:        int = 30
GEMINI_RETRY_ATTEMPTS: int = 2

TOKENS_TAGGER:   int = 600
TOKENS_SUMMARY:  int = 700
TOKENS_INSIGHTS: int = 900
TOKENS_QUESTIONS:int = 800
TOKENS_PYQ_LINK: int = 500

PORT:          int  = int(os.environ.get("PORT", 8000))
API_V1_PREFIX: str  = "/api/v1"
DEBUG:         bool = os.environ.get("DEBUG", "false").lower() == "true"

API_KEYS_RAW: str = os.environ.get("API_KEYS", "dev_key_change_in_production")
API_KEYS: set = {k.strip() for k in API_KEYS_RAW.split(",") if k.strip()}

MAX_ARTICLES_PER_RUN: int = 100
MAX_CONTENT_CHARS:    int = 8000
ANALYSIS_BATCH_SIZE:  int = 10

PRELIMS_RELEVANCE_THRESHOLD: int = 5
MAINS_RELEVANCE_THRESHOLD:   int = 4

GITHUB_TOKEN: str = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO:  str = os.environ.get("GITHUB_REPO",  "")
LOG_LEVEL:    int = logging.DEBUG if DEBUG else logging.INFO
