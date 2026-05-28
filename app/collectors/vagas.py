"""Coletor de vagas em Gupy e Indeed (públicos)."""
from __future__ import annotations
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from app.collectors.base import CollectorResult
from app.utils.http import fetch
from app.utils.logger import get_logger
from app.collectors.linkedin import _classify_area

log = get_logger("collector.vagas")


async def collect_vagas(company: dict) -> CollectorResult:
    res = CollectorResult(source="vagas")
    nome = company.get("empresa")
    if not nome:
        res.error = "sem_empresa"
        return res

    jobs = []
    jobs += await _gupy(nome)
    jobs += await _indeed(nome)
    res.jobs = jobs
    log.info("vagas OK %s jobs=%d", nome, len(jobs))
    return res


async def _gupy(nome: str) -> list[dict]:
    url = f"https://portal.gupy.io/job-search/term={quote_plus(nome)}"
    html = await fetch(url)
    out = []
    if not html:
        return out
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select("a[href*='/job/']")[:30]:
        title = a.get_text(" ", strip=True)
        if title:
            out.append({"title": title, "area": _classify_area(title), "url": a.get("href", "")})
    return out


async def _indeed(nome: str) -> list[dict]:
    url = f"https://br.indeed.com/jobs?q={quote_plus(nome)}"
    html = await fetch(url)
    out = []
    if not html:
        return out
    soup = BeautifulSoup(html, "html.parser")
    for h in soup.select("h2.jobTitle, a.jcs-JobTitle, h2 a")[:30]:
        title = h.get_text(" ", strip=True)
        if title:
            out.append({"title": title, "area": _classify_area(title), "url": ""})
    return out
