"""Baselines por CNAE para normalização.

CNAE Seção (2 primeiros dígitos) → expectativas:
- adm_jobs_baseline: número de vagas administrativas em que se considera "normal"
- operational_share_baseline: fração de vagas operacionais esperada
- units_baseline: número de filiais que se considera "comum" para o setor

Valores são heurísticos e devem ser calibrados com dados reais (rodar análise
descritiva sobre `jobs.xlsx` por CNAE). Ajuste neste arquivo, sem código.
"""
from __future__ import annotations

# Estrutura: prefixo CNAE (2 dígitos) -> baseline dict
BASELINES: dict[str, dict] = {
    "47": {"adm_jobs_baseline": 8, "operational_share_baseline": 0.55, "units_baseline": 50, "rotulo": "Comércio varejista"},
    "46": {"adm_jobs_baseline": 5, "operational_share_baseline": 0.45, "units_baseline": 8,  "rotulo": "Comércio atacadista"},
    "49": {"adm_jobs_baseline": 4, "operational_share_baseline": 0.65, "units_baseline": 6,  "rotulo": "Transporte terrestre"},
    "10": {"adm_jobs_baseline": 4, "operational_share_baseline": 0.60, "units_baseline": 4,  "rotulo": "Indústria alimentos"},
    "20": {"adm_jobs_baseline": 4, "operational_share_baseline": 0.55, "units_baseline": 3,  "rotulo": "Indústria química"},
    "62": {"adm_jobs_baseline": 3, "operational_share_baseline": 0.15, "units_baseline": 2,  "rotulo": "Tecnologia"},
    "64": {"adm_jobs_baseline": 6, "operational_share_baseline": 0.20, "units_baseline": 30, "rotulo": "Serviços financeiros"},
    "85": {"adm_jobs_baseline": 4, "operational_share_baseline": 0.30, "units_baseline": 6,  "rotulo": "Educação"},
    "86": {"adm_jobs_baseline": 6, "operational_share_baseline": 0.45, "units_baseline": 4,  "rotulo": "Saúde"},
    "55": {"adm_jobs_baseline": 4, "operational_search_baseline": 0.55, "units_baseline": 6, "rotulo": "Hospedagem"},
}

# Fallback genérico
DEFAULT_BASELINE = {
    "adm_jobs_baseline": 5,
    "operational_share_baseline": 0.45,
    "units_baseline": 5,
    "rotulo": "Genérico",
}


def baseline_for(cnae: str | None) -> dict:
    if not cnae:
        return DEFAULT_BASELINE
    prefix = str(cnae).strip()[:2]
    return BASELINES.get(prefix, DEFAULT_BASELINE)
