"""Coletor de notícias via Google News RSS.

Gratuito, sem chave, estável. Detecta eventos comerciais e operacionais por
palavras-chave em títulos. Cada notícia recebe categorias (expansao, demissao,
problema, investimento, m_a, contrato_publico).
"""
from __future__ import annotations
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

import httpx
from app.collectors.base import CollectorResult
from app.config import HTTP_TIMEOUT, USER_AGENT
from app.utils.logger import get_logger

log = get_logger("collector.noticias")

RSS_URL = "https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"

CATEGORIES = {
    "expansao": [r"\bexpan", r"\babre filial", r"\bnova unidade", r"\binaugur", r"\bcresce", r"\bcrescimento"],
    "demissao": [r"\bdemiss", r"\blayoff", r"\bdesligamento", r"\bcorte de pessoal", r"\breduç[aã]o de quadro"],
    "investimento": [r"\binvestimento", r"\baporte", r"\brodada", r"\bcaptaç[aã]o", r"\bfunding", r"\bipo\b"],
    "m_a": [r"\baquisiç[aã]o", r"\bcompra", r"\bfusao", r"\bfus[aã]o", r"\bvende\b", r"\bmerge"],
    "problema": [r"\bcrise", r"\brecuperaç[aã]o judicial", r"\bprocesso", r"\bmulta", r"\bautuaç[aã]o", r"\bfalha", r"\bvazamento"],
    "contrato_publico": [r"\blicitaç[aã]o", r"\bcontrato com a uni[aã]o", r"\bgoverno federal", r"\bprefeitura"],
}
COMPILED = {k: [re.compile(p, re.I) for p in v] for k, v in CATEGORIES.items()}


def _classify(title: str) -> list[str]:
    cats = []
    for cat, pats in COMPILED.items():
        if any(p.search(title) for p in pats):
            cats.append(cat)
    return cats


def _age_days(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
        return max(0, (datetime.utcnow() - dt).days)
    except Exception:
        return None


async def collect_noticias(company: dict) -> CollectorResult:
    res = CollectorResult(source="noticias")
    nome = (company.get("empresa") or "").strip()
    if not nome:
        res.error = "sem_empresa"
        return res

    q = f'"{nome}"'
    url = RSS_URL.format(q=quote_plus(q))
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}) as c:
            r = await c.get(url)
        if r.status_code != 200:
            res.error = f"http_{r.status_code}"
            return res
    except Exception as e:
        res.error = f"erro:{e}"
        log.exception("noticias falhou: %s", e)
        return res

    items = []
    try:
        root = ET.fromstring(r.text)
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            source = ""
            src_el = item.find("source")
            if src_el is not None:
                source = (src_el.text or "").strip()
            cats = _classify(title)
            if not cats:
                continue
            items.append({
                "title": title, "url": link, "source": source,
                "published_at": pub, "categories": cats,
                "age_days": _age_days(pub),
            })
            if len(items) >= 25:
                break
    except Exception as e:
        res.error = f"parse:{e}"
        return res

    res.news = items
    # contagem por categoria, usada no scoring
    counts: dict[str, int] = {}
    recent_counts: dict[str, int] = {}
    for it in items:
        for c in it["categories"]:
            counts[c] = counts.get(c, 0) + 1
            if (it.get("age_days") or 9999) <= 180:
                recent_counts[c] = recent_counts.get(c, 0) + 1
    res.meta = {"total": len(items), "by_category": counts, "recent_180d": recent_counts}
    log.info("noticias OK %s total=%d cats=%s", nome, len(items), counts)
    return res
