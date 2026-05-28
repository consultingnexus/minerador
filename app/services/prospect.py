from __future__ import annotations
from pathlib import Path

from app.collectors.maps_discovery import collect_maps_discovery
from app.services.search_config import load_searches
from app.services.exporter import export_prospect_xlsx
from app.utils.logger import get_logger

log = get_logger("service.prospect")


def _key(item: dict) -> str:
    return f"{(item.get('empresa') or '').strip().lower()}|{(item.get('endereco') or '').strip().lower()}"


async def run_prospect() -> Path:
    cfg = load_searches()
    todas: list[dict] = []
    vistos: set[str] = set()

    for spec in cfg.searches:
        items = await collect_maps_discovery(
            setor=spec.setor,
            regiao=spec.regiao,
            max_resultados=spec.max_resultados,
        )
        log.info("busca setor=%s regiao=%s -> %d itens", spec.setor, spec.regiao, len(items))
        for it in items:
            k = _key(it)
            if k in vistos:
                continue
            vistos.add(k)
            todas.append(it)

    if cfg.export.apenas_sem_site:
        filtradas = [c for c in todas if not (c.get("website") or "").strip()]
    else:
        filtradas = todas

    log.info("prospect total=%d sem_site=%d", len(todas), len(filtradas))
    return export_prospect_xlsx(filtradas, arquivo_template=cfg.export.arquivo)
