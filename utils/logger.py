"""utils/logger.py — Rotating file logger."""
import logging, logging.handlers, sys, pathlib

def setup_logging(level=logging.INFO):
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    root.addHandler(ch)
    log_dir = pathlib.Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    try:
        fh = logging.handlers.RotatingFileHandler(
            log_dir / "newspaper_engine.log",
            maxBytes=5*1024*1024, backupCount=3, encoding="utf-8",
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except Exception:
        pass
    for n in ("httpx","httpcore","urllib3","feedparser"):
        logging.getLogger(n).setLevel(logging.WARNING)
