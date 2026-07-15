"""api/auth.py — API Key Authentication."""
import logging
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
import config

logger = logging.getLogger(__name__)
_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def require_api_key(api_key: str | None = Security(_HEADER)) -> str:
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-Key header")
    if api_key not in config.API_KEYS:
        logger.warning("Invalid API key: %s...", api_key[:8])
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return api_key

async def optional_api_key(api_key: str | None = Security(_HEADER)) -> str | None:
    return api_key if api_key and api_key in config.API_KEYS else None
