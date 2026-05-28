import asyncio
import httpx
from app.config import HTTP_TIMEOUT, HTTP_RETRIES, USER_AGENT
from app.utils.logger import get_logger

log = get_logger("http")

# Status codes que indicam falha definitiva — não vale a pena tentar de novo.
NON_RETRYABLE = {400, 401, 403, 404, 410, 451}


async def fetch(url: str, retries: int = HTTP_RETRIES, timeout: float | None = None) -> str | None:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"}
    last_exc = None
    t = timeout if timeout is not None else HTTP_TIMEOUT
    async with httpx.AsyncClient(timeout=t, follow_redirects=True, headers=headers) as client:
        for attempt in range(retries + 1):
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    return r.text
                if r.status_code in NON_RETRYABLE:
                    log.info("GET %s -> %s (não-retentável)", url, r.status_code)
                    return None
                log.warning("GET %s -> %s (tentativa %d)", url, r.status_code, attempt + 1)
            except Exception as e:
                last_exc = e
                log.warning("GET %s attempt %d falhou: %s", url, attempt + 1, e)
            if attempt < retries:
                await asyncio.sleep(0.4 * (attempt + 1))
    if last_exc:
        log.error("GET %s falhou definitivamente: %s", url, last_exc)
    return None
