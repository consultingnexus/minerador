from __future__ import annotations
from datetime import datetime
from pathlib import Path
import pandas as pd

from app.config import COMPANIES_FILE, SCORES_FILE, EXPORTS_DIR, NEWS_FILE
from app.utils.storage import read_df, COMPANY_COLUMNS, SCORE_COLUMNS, NEWS_COLUMNS


def ranking_df() -> pd.DataFrame:
    comps = read_df(COMPANIES_FILE, COMPANY_COLUMNS)
    scores = read_df(SCORES_FILE, SCORE_COLUMNS)
    if scores.empty:
        return pd.DataFrame(columns=["empresa", "score", "confidence", "signals", "observacoes"])
    df = scores.merge(comps, left_on="company_id", right_on="id", how="left", suffixes=("", "_c"))
    cols = [
        "empresa", "cnpj", "setor", "cnae", "porte", "cidade", "uf", "site",
        "score", "confidence",
        "sub_dependencia_administrativa", "sub_processos_repetitivos",
        "sub_problemas_atendimento", "sub_crescimento",
        "sub_complexidade_operacional", "sub_maturidade_digital_baixa",
        "playbook", "trigger_event",
        "signals", "observacoes",
        "resultado_comercial", "nota_comercial",
        "updated_at",
    ]
    cols = [c for c in cols if c in df.columns]
    df = df[cols].sort_values("score", ascending=False).reset_index(drop=True)
    return df


def export_ranking_xlsx() -> Path:
    """Exporta um Excel com:
       - sheet "ranking" (tudo ordenado por score)
       - sheet "alta_prioridade" (score >= 50 e confidence >= 0.5)
       - uma sheet por playbook (segmentação comercial)
       - sheet "noticias" (eventos detectados)
    """
    df = ranking_df()
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = EXPORTS_DIR / f"ranking_{ts}.xlsx"

    news = read_df(NEWS_FILE, NEWS_COLUMNS)

    with pd.ExcelWriter(path, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="ranking")

        if not df.empty:
            prio = df[(df["score"] >= 50) & (df["confidence"] >= 0.5)]
            if not prio.empty:
                prio.to_excel(w, index=False, sheet_name="alta_prioridade")

            if "playbook" in df.columns:
                for pb, group in df.groupby(df["playbook"].fillna("sem_playbook")):
                    sheet = _safe_sheet_name(str(pb))
                    group.to_excel(w, index=False, sheet_name=sheet)

        if not news.empty:
            news.to_excel(w, index=False, sheet_name="noticias")
    return path


PROSPECT_COLUMNS = ["empresa", "setor_busca", "cidade", "endereco", "telefone", "email", "url_maps"]


def export_prospect_xlsx(rows: list[dict], arquivo_template: str = "prospeccao_{timestamp}.xlsx") -> Path:
    """Exporta empresas prospectadas (sem website) para Excel.
    - sheet 'todas' com tudo
    - uma sheet por setor_busca
    """
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    nome = arquivo_template.replace("{timestamp}", ts)
    path = EXPORTS_DIR / nome

    df = pd.DataFrame(rows)
    for col in PROSPECT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[PROSPECT_COLUMNS]

    with pd.ExcelWriter(path, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="todas")
        if not df.empty and "setor_busca" in df.columns:
            for setor, group in df.groupby(df["setor_busca"].fillna("sem_setor")):
                sheet = _safe_sheet_name(str(setor))
                group.to_excel(w, index=False, sheet_name=sheet)
    return path


def _safe_sheet_name(name: str) -> str:
    # Excel: 31 chars max, sem `[]:*?/\`
    bad = '[]:*?/\\'
    cleaned = "".join("_" if c in bad else c for c in name)
    return cleaned[:31] or "sheet"
