"""services/backup.py — GitHub DB backup."""
import asyncio, base64, json, logging, pathlib, urllib.request
from datetime import date
import config

logger = logging.getLogger(__name__)

async def run_backup() -> str:
    if not config.GITHUB_TOKEN or not config.GITHUB_REPO:
        return "Backup skipped — GITHUB_TOKEN/GITHUB_REPO not configured."
    try:
        return await asyncio.to_thread(_backup_sync)
    except Exception as exc:
        logger.exception("Backup failed: %s", exc)
        return f"Backup failed: {exc}"

def _backup_sync() -> str:
    db_path = pathlib.Path(config.DB_PATH)
    if not db_path.exists(): return "Database file not found."
    content = base64.b64encode(db_path.read_bytes()).decode()
    size_kb = db_path.stat().st_size // 1024
    headers = {"Authorization": f"token {config.GITHUB_TOKEN}",
               "Content-Type": "application/json",
               "User-Agent": "UPSC-Newspaper-Engine/1.0"}
    base_url = f"https://api.github.com/repos/{config.GITHUB_REPO}/contents"

    def _push(path: str, msg: str):
        url = f"{base_url}/{path}"
        sha = None
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=10) as r:
                sha = json.loads(r.read().decode()).get("sha")
        except Exception: pass
        payload = {"message": msg, "content": content}
        if sha: payload["sha"] = sha
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers=headers, method="PUT")
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status in (200, 201)

    _push("backup/newspaper.db", f"Auto-backup {date.today()}")
    _push(f"backup/newspaper_{date.today()}.db", f"Dated backup {date.today()}")
    return f"Backup OK | newspaper.db ({size_kb} KB) -> {config.GITHUB_REPO}"
