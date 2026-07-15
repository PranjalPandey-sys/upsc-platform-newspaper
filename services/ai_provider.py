"""services/ai_provider.py — Gemini AI Provider with reasoning fix."""
import asyncio, json, logging, re, time
import config

logger = logging.getLogger(__name__)
_client = None

def _get_client():
    global _client
    if _client is not None: return _client
    if not config.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set"); return None
    try:
        from openai import AsyncOpenAI
        _client = AsyncOpenAI(api_key=config.GEMINI_API_KEY, base_url=config.GEMINI_BASE_URL)
        logger.info("AI provider ready | model=%s", config.GEMINI_MODEL)
        return _client
    except Exception as exc:
        logger.exception("AI client init failed: %s", exc); return None

async def call(system: str, user_msg: str, max_tokens: int = 700,
               temperature: float = 0.2, task_name: str = "unknown") -> tuple:
    client = _get_client()
    if not client: return "", "error", 0
    start = time.monotonic()
    for attempt in range(config.GEMINI_RETRY_ATTEMPTS):
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=config.GEMINI_MODEL,
                    messages=[{"role":"system","content":system},{"role":"user","content":user_msg}],
                    max_tokens=max_tokens, temperature=temperature,
                    extra_body={"reasoning_effort": config.GEMINI_REASONING},
                ),
                timeout=config.GEMINI_TIMEOUT,
            )
            ms = int((time.monotonic() - start) * 1000)
            choice = response.choices[0]
            text = (choice.message.content or "").strip()
            finish = choice.finish_reason or "stop"
            if finish == "length":
                logger.warning("AI truncation | task=%s | max_tokens=%d", task_name, max_tokens)
            logger.debug("AI call | task=%s | finish=%s | %dms", task_name, finish, ms)
            return text, finish, ms
        except asyncio.TimeoutError:
            ms = int((time.monotonic() - start) * 1000)
            logger.warning("AI timeout | task=%s | attempt=%d", task_name, attempt+1)
            if attempt < config.GEMINI_RETRY_ATTEMPTS - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            return "", "timeout", ms
        except Exception as exc:
            ms = int((time.monotonic() - start) * 1000)
            err = str(exc)
            if "429" in err or "quota" in err.lower():
                if attempt < config.GEMINI_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(5 * (attempt+1)); continue
            logger.error("AI call failed | task=%s | %s", task_name, exc)
            return "", "error", ms
    return "", "error", 0

def parse_json_response(text: str, expected_type=dict):
    if not text: return None
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text).strip()
    text = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, expected_type) else None
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse failed: %s | %s", exc, text[:200])
        return None
