"""Coletor Google Maps via Playwright. Tenta extrair rating médio e reviews textuais."""
from __future__ import annotations
import asyncio
from urllib.parse import quote_plus
from app.collectors.base import CollectorResult
from app.utils.logger import get_logger

log = get_logger("collector.google_maps")


async def collect_google_maps(company: dict) -> CollectorResult:
    res = CollectorResult(source="google_maps")
    nome = company.get("empresa")
    cidade = company.get("cidade") or ""
    if not nome:
        res.error = "sem_empresa"
        return res

    query = f"{nome} {cidade}".strip()
    url = f"https://www.google.com/maps/search/{quote_plus(query)}"

    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        res.error = f"playwright_indisponivel:{e}"
        return res

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(locale="pt-BR")
            page = await ctx.new_page()
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(3500)

            # tenta clicar no primeiro card
            try:
                card = page.locator('a[href*="/maps/place/"]').first
                if await card.count() > 0:
                    await card.click()
                    await page.wait_for_timeout(2500)
            except Exception:
                pass

            # rating
            try:
                rating_txt = await page.locator('div.fontDisplayLarge').first.inner_text(timeout=2500)
            except Exception:
                rating_txt = ""

            # reviews textuais via aria-label
            reviews = []
            try:
                spans = await page.locator('span[jscontroller]').all_inner_texts()
                for s in spans:
                    s = (s or "").strip()
                    if 20 < len(s) < 500:
                        reviews.append({"rating": None, "text": s})
                reviews = reviews[:15]
            except Exception:
                pass

            await browser.close()

        res.meta = {"rating": rating_txt}
        res.reviews = reviews
        log.info("gmaps OK %s reviews=%d", query, len(reviews))
    except Exception as e:
        res.error = f"erro:{e}"
        log.warning("gmaps falhou %s: %s", query, e)
    return res
