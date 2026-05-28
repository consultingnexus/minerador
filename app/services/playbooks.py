"""Trigger event + playbook commercial selector.

A engine produz score; este módulo traduz o score em UMA AÇÃO comercial:
- trigger_event: frase humana, pronta para email (linha de abertura)
- playbook: rótulo do pitch a usar
"""
from __future__ import annotations

# Mapeia dimensão dominante -> playbook
PLAYBOOK_BY_DIMENSION = {
    "dependencia_administrativa": "RPA / automação back-office",
    "processos_repetitivos":      "Consultoria de processos",
    "problemas_atendimento":      "CX / experiência do cliente",
    "crescimento":                "Estruturação para escala",
    "complexidade_operacional":   "Operações multi-unidade",
    "maturidade_digital_baixa":   "Transformação digital",
}

PLAYBOOK_FALLBACK = "Diagnóstico operacional inicial"

THRESHOLD_DOMINANT = 35.0  # sub-score mínimo para considerar dimensão dominante


def pick_playbook(scored: dict) -> str:
    sub = scored.get("subscores") or {}
    if not sub:
        return PLAYBOOK_FALLBACK
    top = max(sub.items(), key=lambda kv: kv[1])
    if top[1] < THRESHOLD_DOMINANT:
        return PLAYBOOK_FALLBACK
    return PLAYBOOK_BY_DIMENSION.get(top[0], PLAYBOOK_FALLBACK)


def build_trigger_event(company: dict, scored: dict, outputs: list) -> str:
    """Gera frase humana descrevendo o sinal mais forte."""
    nome = company.get("empresa", "Empresa")
    sub = scored.get("subscores") or {}
    if not sub:
        return f"{nome}: sem sinais coletados ainda."

    by_source = {o.source: o for o in outputs if o.ok}
    noticias = (by_source.get("noticias").meta if "noticias" in by_source else {}) or {}
    pagespeed = (by_source.get("pagespeed").meta if "pagespeed" in by_source else {}) or {}
    site_meta = (by_source.get("site").meta if "site" in by_source else {}) or {}

    top_dim, top_score = max(sub.items(), key=lambda kv: kv[1])

    if top_dim == "dependencia_administrativa":
        return f"{nome} está com alto volume de vagas administrativas abertas — sinal de back-office sobrecarregado."
    if top_dim == "processos_repetitivos":
        return f"{nome} concentra contratações em funções operacionais/repetitivas, oportunidade para automação."
    if top_dim == "problemas_atendimento":
        cat = (noticias.get("recent_180d") or {}).get("problema", 0)
        if cat:
            return f"{nome} apareceu em notícias com sinais negativos de operação nos últimos 6 meses."
        return f"{nome} acumula reviews públicos negativos sobre atendimento e demora."
    if top_dim == "crescimento":
        evid = []
        rec = noticias.get("recent_180d") or {}
        if rec.get("expansao"):
            evid.append(f"{rec['expansao']} notícia(s) de expansão recentes")
        if rec.get("investimento"):
            evid.append(f"{rec['investimento']} notícia(s) de investimento")
        ev = "; ".join(evid) if evid else "alto volume de contratação"
        return f"{nome} em momento de crescimento — {ev}."
    if top_dim == "complexidade_operacional":
        units = int(site_meta.get("units_count") or 0)
        if units:
            return f"{nome} opera com cerca de {units} unidades/filiais — complexidade multi-site relevante."
        return f"{nome} tem porte e estrutura operacional compatíveis com gestão multi-unidade."
    if top_dim == "maturidade_digital_baixa":
        perf = pagespeed.get("performance")
        if perf is not None:
            return f"{nome} apresenta performance digital baixa (PageSpeed mobile = {perf}/100)."
        return f"{nome} aparenta baixa maturidade digital pelo site institucional."
    return f"{nome}: sinal predominante em {top_dim} (score {top_score})."
