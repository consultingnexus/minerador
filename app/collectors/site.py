"""Coletor de site institucional, multi-página.

Baixa home + páginas candidatas (carreiras, sobre, unidades, contato).
Extrai texto agregado e sinais estruturados: existência de página de carreiras,
sinais de múltiplas unidades, presença de canais de atendimento.
"""
from __future__ import annotations
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from app.collectors.base import CollectorResult
from app.utils.http import fetch
from app.utils.logger import get_logger

log = get_logger("collector.site")

CANDIDATE_PATHS = [
    "/", "/carreiras", "/carreira", "/trabalhe-conosco", "/vagas",
    "/sobre", "/sobre-nos", "/empresa", "/quem-somos",
    "/unidades", "/lojas", "/filiais", "/onde-estamos",
    "/contato", "/fale-conosco", "/atendimento",
]

UNIT_PATTERNS = [
    re.compile(r"\b(\d{2,4})\s+(unidades|filiais|lojas|franqueados|pontos de venda|centros)\b", re.I),
    re.compile(r"\bmais de\s+(\d{2,4})\s+(unidades|filiais|lojas|franqueados)\b", re.I),
]
CAREER_KEYWORDS = ("carreira", "trabalhe conosco", "trabalhe-conosco", "vagas abertas", "junte-se", "venha trabalhar")
SUPPORT_KEYWORDS = ("atendimento", "fale conosco", "central de", "sac", "ouvidoria", "suporte")
DIGITAL_MATURITY_KEYWORDS = ("api", "integração", "integracao", "portal do cliente", "área do cliente", "app", "aplicativo")


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    return url.rstrip("/")


async def _try_paths(base: str) -> dict:
    pages = {}
    # Tenta a home primeiro. Se 403/404, provavelmente é bot wall — aborta.
    home_html = await fetch(base + "/")
    if not home_html:
        return pages
    soup = BeautifulSoup(home_html, "html.parser")
    text = soup.get_text(" ", strip=True).lower()
    if text and len(text) > 100:
        pages["/"] = {"url": base + "/", "len": len(text), "text": text[:8000]}

    for path in CANDIDATE_PATHS[1:]:
        url = urljoin(base + "/", path.lstrip("/"))
        html = await fetch(url, retries=0)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True).lower()
        if text and len(text) > 100:
            pages[path] = {"url": url, "len": len(text), "text": text[:8000]}
        if len(pages) >= 4:
            break
    return pages


def _detect_units(text: str) -> int:
    best = 0
    for pat in UNIT_PATTERNS:
        for m in pat.finditer(text):
            try:
                n = int(m.group(1))
                if 2 <= n <= 50000:
                    best = max(best, n)
            except Exception:
                pass
    return best


async def collect_site(company: dict) -> CollectorResult:
    res = CollectorResult(source="site")
    base = _normalize_url(company.get("site") or "")
    if not base:
        res.error = "sem_site"
        return res

    parsed = urlparse(base)
    if not parsed.netloc:
        res.error = "site_invalido"
        return res

    pages = await _try_paths(base)
    if not pages:
        res.error = "fetch_falhou"
        return res

    full_text = " ".join(p["text"] for p in pages.values())
    units = _detect_units(full_text)
    has_careers = "/carreiras" in pages or "/trabalhe-conosco" in pages or "/vagas" in pages \
        or any(k in full_text for k in CAREER_KEYWORDS)
    has_support = any(k in full_text for k in SUPPORT_KEYWORDS)
    digital_hits = sum(1 for k in DIGITAL_MATURITY_KEYWORDS if k in full_text)

    res.meta = {
        "pages_fetched": list(pages.keys()),
        "total_text_len": len(full_text),
        "units_count": units,
        "has_careers_page": has_careers,
        "has_support_channel": has_support,
        "digital_maturity_hits": digital_hits,
        "raw_text_sample": full_text[:5000],
    }
    log.info("site OK %s pages=%d len=%d units=%d careers=%s digital=%d",
             base, len(pages), len(full_text), units, has_careers, digital_hits)
    return res
