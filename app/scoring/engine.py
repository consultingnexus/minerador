"""Engine de scoring baseada em regras (sem IA).

Diferenciais:
- Sub-scores 0-100 por dimensão, depois ponderados para o composto
- Normalização por CNAE (baselines em baselines.py)
- Negação simples ("não houve demora" não conta)
- Decay temporal para sinais com idade (news/reviews/jobs com age_days)
- Confidence = fração de coletores escolhidos que retornaram OK
"""
from __future__ import annotations
import math
import re

from app.scoring.weights import (
    WEIGHTS, NEG_REVIEW_KEYWORDS, NEGATIONS, REPETITIVE_AREAS, HALF_LIFE_DAYS,
)
from app.scoring.baselines import baseline_for


def _decay(age_days: float | int | None) -> float:
    if age_days is None:
        return 1.0
    try:
        return 0.5 ** (float(age_days) / HALF_LIFE_DAYS)
    except Exception:
        return 1.0


def _neg_keyword_hits(text: str) -> int:
    """Conta hits de palavras-chave negativas com checagem simples de negação:
    se um dos termos de negação aparece nos 4 tokens anteriores, o hit é descartado.
    """
    if not text:
        return 0
    t = text.lower()
    tokens = re.findall(r"[a-zà-ÿ0-9]+", t)
    if not tokens:
        return 0
    hits = 0
    joined = " " + " ".join(tokens) + " "
    for kw in NEG_REVIEW_KEYWORDS:
        idx = joined.find(" " + kw)
        while idx != -1:
            preceding = joined[max(0, idx - 60):idx]
            pre_tokens = preceding.split()[-4:]
            if not any(n in pre_tokens for n in NEGATIONS):
                hits += 1
            idx = joined.find(" " + kw, idx + 1)
    return hits


def score_company(company: dict, collector_outputs: list, chosen_collectors: list[str] | None = None) -> dict:
    """Retorna: { score, confidence, subscores, signals, observacoes }."""
    chosen = chosen_collectors or []
    by_source = {o.source: o for o in collector_outputs}
    ok_sources = {o.source for o in collector_outputs if o.ok}
    confidence = round(len(ok_sources) / max(1, len(chosen)), 2) if chosen else 1.0

    reviews_all = []
    jobs_all = []
    site_meta = (by_source.get("site").meta if "site" in by_source and by_source["site"].ok else {}) or {}
    cnpj_meta = (by_source.get("cnpj").meta if "cnpj" in by_source and by_source["cnpj"].ok else {}) or {}
    pagespeed_meta = (by_source.get("pagespeed").meta if "pagespeed" in by_source and by_source["pagespeed"].ok else {}) or {}
    noticias_meta = (by_source.get("noticias").meta if "noticias" in by_source and by_source["noticias"].ok else {}) or {}

    for o in collector_outputs:
        if not o.ok:
            continue
        reviews_all += [{"source": o.source, **r} for r in o.reviews]
        jobs_all += [{"source": o.source, **j} for j in o.jobs]

    cnae = (company.get("cnae") or cnpj_meta.get("cnae"))
    baseline = baseline_for(cnae)
    porte = (company.get("porte") or cnpj_meta.get("porte") or "").upper()

    sub = {k: 0.0 for k in WEIGHTS.keys()}
    signals: list[str] = []

    # --- 1) Problemas de atendimento (reviews + notícias categoria 'problema') ---
    neg_hits = 0.0
    for r in reviews_all:
        h = _neg_keyword_hits(r.get("text") or "")
        if h:
            neg_hits += h * _decay(r.get("age_days"))
    cat_problem_recent = (noticias_meta.get("recent_180d") or {}).get("problema", 0)
    if cat_problem_recent:
        neg_hits += cat_problem_recent * 2  # peso maior pra problemas em notícias recentes
    if neg_hits > 0:
        sub["problemas_atendimento"] = min(100.0, neg_hits * 20.0)
        signals.append(f"problemas_atendimento(hits={neg_hits:.1f})")

    # --- 2) Dependência administrativa (normalizada por baseline do CNAE) ---
    adm_jobs = [j for j in jobs_all if j.get("area") == "administrativo"]
    if adm_jobs:
        adm_count = sum(_decay(j.get("age_days")) for j in adm_jobs)
        ratio = adm_count / max(1.0, float(baseline["adm_jobs_baseline"]))
        if ratio >= 1.0:
            sub["dependencia_administrativa"] = min(100.0, 50.0 + (ratio - 1.0) * 25.0)
            signals.append(f"dependencia_administrativa(adm={adm_count:.1f} vs base={baseline['adm_jobs_baseline']})")

    # --- 3) Processos repetitivos (share operacional+adm acima do baseline) ---
    if jobs_all:
        rep = sum(_decay(j.get("age_days")) for j in jobs_all if j.get("area") in REPETITIVE_AREAS)
        total = sum(_decay(j.get("age_days")) for j in jobs_all)
        share = rep / total if total else 0
        excess = share - float(baseline["operational_share_baseline"])
        if excess > 0.05:
            sub["processos_repetitivos"] = min(100.0, excess * 200.0)
            signals.append(f"processos_repetitivos(share={share:.2f} excesso={excess:.2f})")

    # --- 4) Crescimento (notícias de expansão/investimento, idade decai) ---
    growth_score = 0.0
    cat_recent = noticias_meta.get("recent_180d") or {}
    growth_score += cat_recent.get("expansao", 0) * 25
    growth_score += cat_recent.get("investimento", 0) * 20
    growth_score += cat_recent.get("m_a", 0) * 15
    # adicional: muitas vagas no total
    job_volume = sum(_decay(j.get("age_days")) for j in jobs_all)
    if job_volume >= 10:
        growth_score += min(40.0, (job_volume - 10) * 2.0)
    if growth_score > 0:
        sub["crescimento"] = min(100.0, growth_score)
        evid = []
        if cat_recent.get("expansao"):     evid.append(f"expansao={cat_recent['expansao']}")
        if cat_recent.get("investimento"): evid.append(f"investimento={cat_recent['investimento']}")
        if job_volume >= 10:               evid.append(f"vagas={int(job_volume)}")
        signals.append(f"crescimento({', '.join(evid) or 'sinal misto'})")

    # --- 5) Complexidade operacional (filiais + porte + capital) ---
    units = int(site_meta.get("units_count") or 0)
    complex_score = 0.0
    units_base = float(baseline["units_baseline"])
    if units >= 3:
        ratio = units / units_base
        complex_score += min(70.0, ratio * 30.0)
    if porte in ("DEMAIS", "GRANDE PORTE"):
        complex_score += 20.0
    capital = cnpj_meta.get("capital_social")
    if capital and isinstance(capital, (int, float)) and capital >= 5_000_000:
        complex_score += 10.0
    if complex_score > 0:
        sub["complexidade_operacional"] = min(100.0, complex_score)
        signals.append(f"complexidade_operacional(unidades={units}, porte={porte or 'N/D'})")

    # --- 6) Maturidade digital baixa (PageSpeed + site fraco) ---
    perf = pagespeed_meta.get("performance")
    seo = pagespeed_meta.get("seo")
    bp = pagespeed_meta.get("best_practices")
    digital_score = 0.0
    has_any_perf = any(v is not None for v in (perf, seo, bp))
    if has_any_perf:
        avg = sum(v for v in (perf, seo, bp) if v is not None) / sum(1 for v in (perf, seo, bp) if v is not None)
        if avg < 70:
            digital_score += (70 - avg) * 1.2  # 0 a ~84
    if site_meta:
        if site_meta.get("total_text_len", 0) < 1500:
            digital_score += 15
        if not site_meta.get("has_careers_page"):
            digital_score += 10
        if (site_meta.get("digital_maturity_hits") or 0) < 1:
            digital_score += 10
    if digital_score > 0:
        sub["maturidade_digital_baixa"] = min(100.0, digital_score)
        evid = []
        if has_any_perf:
            evid.append(f"pagespeed_avg={round(avg, 1)}")
        evid.append(f"site_len={site_meta.get('total_text_len', 0)}")
        signals.append(f"maturidade_digital_baixa({', '.join(evid)})")

    # --- Score composto ---
    total_weight = sum(WEIGHTS.values())
    composite = sum(sub[k] * WEIGHTS[k] for k in WEIGHTS) / total_weight
    composite = round(max(0.0, min(100.0, composite)), 1)

    sub = {k: round(v, 1) for k, v in sub.items()}
    obs = "; ".join(signals) if signals else "sem sinais relevantes"

    return {
        "score": composite,
        "confidence": confidence,
        "subscores": sub,
        "signals": signals,
        "observacoes": obs,
        "_baseline_rotulo": baseline.get("rotulo"),
    }
