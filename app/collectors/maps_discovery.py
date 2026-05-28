"""Coletor de descoberta no Google Maps.

Usa a API SÍNCRONA do Playwright rodando em uma thread separada via
asyncio.to_thread. Isso evita o NotImplementedError do asyncio.subprocess
em Windows quando o event loop não é Proactor (uvicorn/anyio às vezes
substitui o policy).
"""
from __future__ import annotations
import asyncio
from urllib.parse import quote_plus

from app.utils.logger import get_logger

log = get_logger("collector.maps_discovery")


def _scrape_sync(setor: str, regiao: str, max_resultados: int) -> list[dict]:
    """Executa scraping síncrono — chamado de dentro de uma thread."""
    query = f"{setor} {regiao}".strip()
    url = f"https://www.google.com/maps/search/{quote_plus(query)}"
    resultados: list[dict] = []

    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        log.warning("playwright indisponível: %s", e)
        return []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(locale="pt-BR")
            page = ctx.new_page()
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)

            # Aceitar/rejeitar cookies e fechar overlays comuns
            for sel in [
                'button:has-text("Aceitar tudo")',
                'button:has-text("Accept all")',
                'button:has-text("Rejeitar tudo")',
                'button:has-text("Reject all")',
                'button[aria-label*="Aceitar"]',
                'button[aria-label*="Accept"]',
            ]:
                try:
                    b = page.locator(sel).first
                    if b.count() > 0:
                        b.click(timeout=2000)
                        page.wait_for_timeout(800)
                        break
                except Exception:
                    continue

            feed = page.locator('div[role="feed"]').first
            try:
                feed.wait_for(timeout=8000)
            except Exception:
                log.warning("feed do Maps não apareceu para query=%s", query)
                browser.close()
                return []

            # Scroll até obter ao menos max_resultados cards ou esgotar
            for _ in range(40):
                cards = page.locator('div[role="feed"] a[href*="/maps/place/"]')
                cnt = cards.count()
                if cnt >= max_resultados:
                    break
                try:
                    feed.evaluate("el => el.scrollBy(0, 2000)")
                except Exception:
                    pass
                page.wait_for_timeout(1200)

            cards = page.locator('div[role="feed"] a[href*="/maps/place/"]')
            total = min(cards.count(), max_resultados)
            log.info(
                "maps_discovery query=%s cards=%d (limite=%d)",
                query, total, max_resultados,
            )

            # Mudança 1: pré-captura aria-label + href de cada card UMA vez.
            # Isso imuniza contra re-render do feed após cliques.
            card_refs: list[dict] = []
            for i in range(total):
                try:
                    c = cards.nth(i)
                    card_refs.append({
                        "aria_nome": (c.get_attribute("aria-label") or "").strip(),
                        "href": (c.get_attribute("href") or "").strip(),
                    })
                except Exception:
                    card_refs.append({"aria_nome": "", "href": ""})

            for i, ref in enumerate(card_refs):
                aria_nome = ref["aria_nome"]
                href = ref["href"]
                try:
                    card = cards.nth(i)
                    card.scroll_into_view_if_needed(timeout=3000)

                    # Mudança 2: aguardar URL REALMENTE mudar (não só casar padrão).
                    prev_url = page.url
                    # overlay (bzPs2e) intercepta clique real — dispara via JS
                    card.evaluate("el => el.click()")
                    url_changed = True
                    try:
                        page.wait_for_function(
                            "(prev) => location.href !== prev && location.href.includes('/maps/place/')",
                            arg=prev_url,
                            timeout=8000,
                        )
                    except Exception:
                        url_changed = False

                    # Mudança 5: fallback — se URL não mudou e temos href, navega direto.
                    if not url_changed and href:
                        try:
                            page.goto(href, timeout=20000, wait_until="domcontentloaded")
                            url_changed = page.url != prev_url
                        except Exception:
                            pass

                    # Mudança 3: espera o painel de contatos (data-item-id) renderizar.
                    # data-item-id é o que confirma que a ficha de contatos montou.
                    try:
                        page.locator('div[role="main"] h1').first.wait_for(timeout=6000)
                    except Exception:
                        pass
                    try:
                        page.locator('div[role="main"] [data-item-id]').first.wait_for(timeout=4000)
                    except Exception:
                        page.wait_for_timeout(500)

                    nome = ""
                    try:
                        nome = page.locator('div[role="main"] h1').first.inner_text(timeout=2500).strip()
                    except Exception:
                        pass
                    # fallback: aria-label do card (capturado ANTES do click)
                    if not nome or nome.lower() == "resultados":
                        nome = aria_nome

                    # Só lê detalhes se URL realmente mudou — evita contaminação
                    # com dados da ficha anterior.
                    if url_changed:
                        endereco = _by_data_item(page, "address") or _aria_sync(page, "Endereço") or _aria_sync(page, "Address")
                        telefone = _by_data_item(page, "phone:tel:") or _aria_sync(page, "Telefone") or _aria_sync(page, "Phone")
                        website = _website_sync(page)
                        url_maps = page.url
                    else:
                        endereco = ""
                        telefone = ""
                        website = ""
                        url_maps = href or page.url

                    # Mudança 4: sempre emite se temos pelo menos o nome do card.
                    nome = nome or aria_nome
                    if not nome:
                        continue

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
                    # Mesmo no erro, ainda emite o que sabemos do card.
                    if aria_nome:
                        resultados.append({
                            "empresa": aria_nome,
                            "endereco": "",
                            "telefone": "",
                            "website": "",
                            "url_maps": href,
                            "cidade": regiao,
                            "setor_busca": setor,
                        })
                    continue

            browser.close()
    except Exception as e:
        log.warning("maps_discovery falhou query=%s: %s", query, e)

    return resultados


def _aria_sync(page, needle: str) -> str:
    """Lê aria-label de botões cujo label contém 'needle' (case-sensitive). Retorna parte após ':'"""
    try:
        loc = page.locator(f'button[aria-label*="{needle}"]').first
        if loc.count() == 0:
            return ""
        aria = loc.get_attribute("aria-label") or ""
        return aria.split(":", 1)[1].strip() if ":" in aria else aria.strip()
    except Exception:
        return ""


def _by_data_item(page, item_id_prefix: str) -> str:
    """Lê aria-label de botões com data-item-id começando por 'item_id_prefix' (ex.: 'address', 'phone:tel:')."""
    try:
        loc = page.locator(f'button[data-item-id^="{item_id_prefix}"]').first
        if loc.count() == 0:
            return ""
        aria = loc.get_attribute("aria-label") or ""
        return aria.split(":", 1)[1].strip() if ":" in aria else aria.strip()
    except Exception:
        return ""


def _website_sync(page) -> str:
    try:
        loc = page.locator('a[data-item-id="authority"]').first
        if loc.count() > 0:
            href = loc.get_attribute("href")
            if href:
                return href
        loc2 = page.locator(
            'a[aria-label^="Site:"], a[aria-label^="Website:"]'
        ).first
        if loc2.count() > 0:
            href = loc2.get_attribute("href")
            if href:
                return href
    except Exception:
        pass
    return ""


async def collect_maps_discovery(
    setor: str, regiao: str, max_resultados: int = 30
) -> list[dict]:
    """Wrapper async — roda o scraper síncrono em uma thread separada."""
    return await asyncio.to_thread(_scrape_sync, setor, regiao, max_resultados)
