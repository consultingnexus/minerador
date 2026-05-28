"""Coletor de descoberta no Google Maps.

Diferente de google_maps.py (que enriquece UMA empresa), aqui recebemos uma
busca (setor + região) e devolvemos uma LISTA de empresas com:
empresa, endereco, telefone, website, url_maps, cidade, setor_busca.
"""
from __future__ import annotations
import re
from urllib.parse import quote_plus

from app.utils.logger import get_logger

log = get_logger("collector.maps_discovery")


async def collect_maps_discovery(setor: str, regiao: str, max_resultados: int = 30) -> list[dict]:
    query = f"{setor} {regiao}".strip()
    url = f"https://www.google.com/maps/search/{quote_plus(query)}"

    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        log.warning("playwright indisponível: %s", e)
        return []

    resultados: list[dict] = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(locale="pt-BR")
            page = await ctx.new_page()
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(3500)

            # Aceitar cookies se aparecer
            try:
                btn = page.locator('button:has-text("Aceitar tudo"), button:has-text("Accept all")').first
                if await btn.count() > 0:
                    await btn.click()
                    await page.wait_for_timeout(1000)
            except Exception:
                pass

            feed = page.locator('div[role="feed"]').first
            try:
                await feed.wait_for(timeout=8000)
            except Exception:
                log.warning("feed do Maps não apareceu para query=%s", query)
                await browser.close()
                return []

            # Scroll até obter ao menos max_resultados cards ou esgotar
            seen_count = 0
            for _ in range(40):
                cards = page.locator('div[role="feed"] a[href*="/maps/place/"]')
                cnt = await cards.count()
                if cnt >= max_resultados:
                    break
                if cnt == seen_count:
                    # tenta scroll mesmo assim algumas vezes
                    pass
                seen_count = cnt
                try:
                    await feed.evaluate("el => el.scrollBy(0, 2000)")
                except Exception:
                    pass
                await page.wait_for_timeout(1200)

            cards = page.locator('div[role="feed"] a[href*="/maps/place/"]')
            total = min(await cards.count(), max_resultados)
            log.info("maps_discovery query=%s cards=%d (limite=%d)", query, total, max_resultados)

            for i in range(total):
                try:
                    card = cards.nth(i)
                    await card.scroll_into_view_if_needed(timeout=3000)
                    await card.click(timeout=5000)
                    await page.wait_for_timeout(1800)

                    nome = ""
                    try:
                        nome = (await page.locator('h1').first.inner_text(timeout=2500)).strip()
                    except Exception:
                        pass

                    endereco = _extract_aria(page, "Endereço:") or _extract_aria(page, "Address:")
                    telefone = _extract_aria(page, "Telefone:") or _extract_aria(page, "Phone:")
                    website = await _extract_website(page)

                    url_maps = page.url

                    if nome:
                        resultados.append({
                            "empresa": nome,
                            "endereco": endereco,
                            "telefone": telefone,
                            "website": website,
                            "url_maps": url_maps,
                            "cidade": regiao,
                            "setor_busca": setor,
                        })
                except Exception as e:
                    log.debug("falha card %d: %s", i, e)
                    continue

            await browser.close()
    except Exception as e:
        log.warning("maps_discovery falhou query=%s: %s", query, e)

    return resultados


async def _extract_aria(page, prefix: str) -> str:
    """Lê botões com aria-label começando por 'Endereço:' / 'Telefone:' etc."""
    try:
        loc = page.locator(f'button[aria-label^="{prefix}"]').first
        if await loc.count() == 0:
            return ""
        aria = await loc.get_attribute("aria-label")
        if not aria:
            return ""
        return aria.split(":", 1)[1].strip()
    except Exception:
        return ""


async def _extract_website(page) -> str:
    """O botão 'Site' aparece como link com data-item-id='authority' ou aria-label='Site:'."""
    try:
        loc = page.locator('a[data-item-id="authority"]').first
        if await loc.count() > 0:
            href = await loc.get_attribute("href")
            if href:
                return href
        loc2 = page.locator('a[aria-label^="Site:"], a[aria-label^="Website:"]').first
        if await loc2.count() > 0:
            href = await loc2.get_attribute("href")
            if href:
                return href
    except Exception:
        pass
    return ""
