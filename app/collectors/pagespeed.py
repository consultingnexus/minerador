"""Coletor Google PageSpeed Insights.

Gratuito com chave (env PAGESPEED_API_KEY); funciona sem chave em rate limit baixo.
Retorna scores objetivos de performance / accessibility / best-practices / SEO,
que viram input direto para o sub-score de maturidade digital.
"""
from __future__ import annotations
import httpx
from app.collectors.base import CollectorResult
from app.config import HTTP_TIMEOUT, PAGESPEED_API_KEY
from app.utils.logger import get_logger

log = get_logger("collector.pagespeed")

ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


async def collect_pagespeed(company: dict) -> CollectorResult:
    res = CollectorResult(source="pagespeed")
    site = (company.get("site") or "").strip()
    if not site:
        res.error = "sem_site"
        return res
    if not site.startswith("http"):
        site = "https://" + site

    params = {"url": site, "strategy": "mobile",
              "category": ["performance", "accessibility", "best-practices", "seo"]}
    if PAGESPEED_API_KEY:
        params["key"] = PAGESPEED_API_KEY

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as c:
            r = await c.get(ENDPOINT, params=params)
        if r.status_code != 200:
            res.error = f"http_{r.status_code}"
            log.warning("pagespeed %s -> %s", site, r.status_code)
            return res
        data = r.json()
    except Exception as e:
        res.error = f"erro:{e}"
        log.exception("pagespeed falhou: %s", e)
        return res

    cats = (data.get("lighthouseResult") or {}).get("categories") or {}
    def s(name: str) -> float | None:
        v = (cats.get(name) or {}).get("score")
        return round(float(v) * 100, 1) if v is not None else None

    res.meta = {
        "performance": s("performance"),
        "accessibility": s("accessibility"),
        "best_practices": s("best-practices"),
        "seo": s("seo"),
    }
    log.info("pagespeed OK %s perf=%s a11y=%s bp=%s seo=%s",
             site, res.meta["performance"], res.meta["accessibility"],
             res.meta["best_practices"], res.meta["seo"])
    return res
