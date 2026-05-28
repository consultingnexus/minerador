"""Coletor ReclameAqui: busca a página da empresa e extrai trechos de reclamações."""
from __future__ import annotations
import re
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from app.collectors.base import CollectorResult
from app.utils.http import fetch
from app.utils.logger import get_logger

log = get_logger("collector.reclame_aqui")


def _slug(nome: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", nome.lower()).strip("-")
    return s


async def collect_reclame_aqui(company: dict) -> CollectorResult:
    res = CollectorResult(source="reclame_aqui")
    nome = company.get("empresa")
    if not nome:
        res.error = "sem_empresa"
        return res

    # tenta página direta
    url = f"https://www.reclameaqui.com.br/empresa/{_slug(nome)}/"
    html = await fetch(url)
    if not html:
        # fallback: busca
        url = f"https://www.reclameaqui.com.br/busca/?q={quote_plus(nome)}"
        html = await fetch(url)
    if not html:
        res.error = "fetch_falhou"
        return res

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    reviews = []
    for p in soup.find_all(["p", "h2", "h3"]):
        t = p.get_text(" ", strip=True)
        if 25 < len(t) < 400 and any(
            k in t.lower() for k in ("demora", "atraso", "atendimento", "problema", "reclamacao", "reclamação")
        ):
            reviews.append({"rating": None, "text": t})
    reviews = reviews[:20]

    res.reviews = reviews
    res.meta = {"page_len": len(text)}
    log.info("reclameaqui OK %s reviews=%d", nome, len(reviews))
    return res
