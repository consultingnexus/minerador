from __future__ import annotations
import time
from datetime import datetime

from app.collectors import COLLECTORS
from app.scoring.engine import score_company
from app.config import REVIEWS_FILE, JOBS_FILE, SCORES_FILE, NEWS_FILE, DEFAULT_COLLECTORS
from app.utils.storage import (
    upsert, REVIEW_COLUMNS, JOB_COLUMNS, SCORE_COLUMNS, NEWS_COLUMNS,
)
from app.utils.logger import get_logger
from app.services.companies import list_companies, update_company_meta
from app.services.playbooks import build_trigger_event, pick_playbook

log = get_logger("analyzer")


async def analyze_companies(company_ids: list[str] | None = None,
                            collectors: list[str] | None = None) -> list[dict]:
    df = list_companies()
    if df.empty:
        return []
    if company_ids:
        df = df[df["id"].isin(company_ids)]
    if df.empty:
        return []

    chosen = collectors or DEFAULT_COLLECTORS
    chosen = [c for c in chosen if c in COLLECTORS]

    results = []
    for _, row in df.iterrows():
        company = {k: (None if (isinstance(v, float) and v != v) else v) for k, v in row.to_dict().items()}
        t0 = time.time()
        log.info("ANALISANDO empresa=%s id=%s coletores=%s",
                 company["empresa"], company["id"], chosen)

        outputs = []
        for name in chosen:
            fn = COLLECTORS[name]
            try:
                r = await fn(company)
            except Exception as e:
                log.exception("coletor %s falhou: %s", name, e)
                continue
            outputs.append(r)
            log.info("coletor=%s status=%s reviews=%d jobs=%d news=%d",
                     name, ("erro:" + r.error) if r.error else "ok",
                     len(r.reviews), len(r.jobs), len(r.news))

            # propaga dados cadastrais para a tabela companies
            if name == "cnpj" and r.ok:
                meta = r.meta or {}
                update_company_meta(company["id"], {
                    "cnae": meta.get("cnae"),
                    "porte": meta.get("porte"),
                    "uf": meta.get("uf"),
                    "data_abertura": meta.get("data_abertura"),
                    "setor": company.get("setor") or meta.get("cnae_descricao"),
                })
                # injeta no dict local para o engine usar
                company["cnae"] = meta.get("cnae") or company.get("cnae")
                company["porte"] = meta.get("porte") or company.get("porte")

        _persist_collector_outputs(company["id"], outputs)
        scored = score_company(company, outputs, chosen_collectors=chosen)
        trigger = build_trigger_event(company, scored, outputs)
        playbook = pick_playbook(scored)
        scored["trigger_event"] = trigger
        scored["playbook"] = playbook
        _persist_score(company, scored)

        results.append({
            "company_id": company["id"],
            "empresa": company["empresa"],
            **scored,
            "elapsed_sec": round(time.time() - t0, 2),
        })
        log.info("score empresa=%s score=%.1f confidence=%.2f playbook=%s",
                 company["empresa"], scored["score"], scored["confidence"], playbook)
    return results


def _persist_collector_outputs(company_id: str, outputs: list) -> None:
    now = datetime.utcnow().isoformat()
    rev_rows, job_rows, news_rows = [], [], []
    for o in outputs:
        for r in o.reviews:
            rev_rows.append({
                "company_id": company_id, "source": o.source,
                "rating": r.get("rating"), "text": r.get("text"),
                "collected_at": now,
            })
        for j in o.jobs:
            job_rows.append({
                "company_id": company_id, "source": o.source,
                "title": j.get("title"), "area": j.get("area"),
                "url": j.get("url"), "collected_at": now,
            })
        for n in o.news:
            news_rows.append({
                "company_id": company_id,
                "title": n.get("title"), "url": n.get("url"),
                "source": n.get("source"), "published_at": n.get("published_at"),
                "categories": "|".join(n.get("categories") or []),
                "collected_at": now,
            })
    if rev_rows:
        upsert(REVIEWS_FILE, rev_rows, REVIEW_COLUMNS, key=["company_id", "source", "text"])
    if job_rows:
        upsert(JOBS_FILE, job_rows, JOB_COLUMNS, key=["company_id", "source", "title"])
    if news_rows:
        upsert(NEWS_FILE, news_rows, NEWS_COLUMNS, key=["company_id", "url"])


def _persist_score(company: dict, scored: dict) -> None:
    sub = scored["subscores"]
    upsert(SCORES_FILE, [{
        "company_id": company["id"],
        "empresa": company["empresa"],
        "score": scored["score"],
        "confidence": scored["confidence"],
        "sub_dependencia_administrativa": sub["dependencia_administrativa"],
        "sub_processos_repetitivos": sub["processos_repetitivos"],
        "sub_problemas_atendimento": sub["problemas_atendimento"],
        "sub_crescimento": sub["crescimento"],
        "sub_complexidade_operacional": sub["complexidade_operacional"],
        "sub_maturidade_digital_baixa": sub["maturidade_digital_baixa"],
        "signals": "; ".join(scored["signals"]),
        "observacoes": scored["observacoes"],
        "trigger_event": scored.get("trigger_event"),
        "playbook": scored.get("playbook"),
        "resultado_comercial": None,
        "nota_comercial": None,
        "updated_at": datetime.utcnow().isoformat(),
    }], SCORE_COLUMNS, key="company_id")
