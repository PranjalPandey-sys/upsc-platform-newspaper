"""utils/helpers.py — General utilities."""
import hashlib, re, unicodedata, email.utils
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

def now_utc(): return datetime.now(timezone.utc)
def now_ist(): return datetime.now(IST)
def iso_now(): return now_utc().isoformat()
def today_ist_str(): return now_ist().date().isoformat()

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def clean_text(text: str) -> str:
    if not text: return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    for pat in [r"Subscribe to.*?newsletter", r"Follow us on.*", r"Click here to.*", r"Disclaimer.*"]:
        text = re.sub(pat, "", text, flags=re.IGNORECASE | re.DOTALL)
    return text.strip()

def truncate(text: str, max_chars: int) -> str:
    if not text or len(text) <= max_chars: return text
    t = text[:max_chars]
    ls = t.rfind(" ")
    return (t[:ls] if ls > 0 else t) + " …"

def parse_feed_date(date_str) -> str:
    if not date_str: return iso_now()
    try:
        return email.utils.parsedate_to_datetime(date_str).astimezone(timezone.utc).isoformat()
    except Exception: pass
    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%d %b %Y"]:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError: continue
    return iso_now()

def content_hash(title: str, url: str) -> str:
    return sha256(f"{title.strip().lower()}|{url.strip().lower()}")

def safe_json(value) -> str:
    import json
    if isinstance(value, (list, dict)): return json.dumps(value, ensure_ascii=False)
    return str(value) if value is not None else "[]"
