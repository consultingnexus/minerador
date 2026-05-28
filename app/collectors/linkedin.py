"""Coletor LinkedIn (público). Pega a página /jobs e a página da empresa, se disponíveis."""
from __future__ import annotations
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from app.collectors.base import CollectorResult
from app.utils.http import fetch
from app.utils.logger import get_logger

log = get_logger("collector.linkedin")


async def collect_linkedin(company: dict) -> CollectorResult:
    res = CollectorResult(source="linkedin")
    nome = company.get("empresa")
    if not nome:
        res.error = "sem_empresa"
        return res

    url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(nome)}&location=Brazil"
    html = await fetch(url)
    if not html:
        res.error = "fetch_falhou"
        return res

    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for card in soup.select("li, div.base-search-card"):
        title_el = card.find(["h3", "h2"])
        if not title_el:
            continue
        title = title_el.get_text(" ", strip=True)
        if not title or len(title) < 3:
            continue
        link_el = card.find("a", href=True)
        href = link_el["href"] if link_el else ""
        area = _classify_area(title)
        jobs.append({"title": title, "area": area, "url": href})
        if len(jobs) >= 30:
            break

    res.jobs = jobs
    log.info("linkedin OK %s jobs=%d", nome, len(jobs))
    return res


def _classify_area(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ("admin", "auxiliar", "assistente", "back office", "financeiro", "contabil", "contábil", "rh", "recursos humanos")):
        return "administrativo"
    if any(k in t for k in ("vendas", "comercial", "consultor")):
        return "comercial"
    if any(k in t for k in ("operac", "logistic", "estoque", "almox")):
        return "operacional"
    if any(k in t for k in ("dev", "engenhe", "engineer", "tech", "ti", "dados", "data")):
        return "tecnologia"
    return "outros"
