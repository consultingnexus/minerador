"""Excel/CSV-based storage. Sem ORM, sem DB. Append + dedup por chave."""
from __future__ import annotations
import threading
from pathlib import Path
import pandas as pd

_lock = threading.Lock()

COMPANY_COLUMNS = [
    "id", "empresa", "cnpj", "setor", "cnae", "porte", "cidade", "uf",
    "site", "telefone", "linkedin", "filiais_count", "data_abertura",
    "created_at",
]
REVIEW_COLUMNS = ["company_id", "source", "rating", "text", "collected_at"]
JOB_COLUMNS = ["company_id", "source", "title", "area", "url", "collected_at"]
SCORE_COLUMNS = [
    "company_id", "empresa", "score", "confidence",
    "sub_dependencia_administrativa", "sub_processos_repetitivos",
    "sub_problemas_atendimento", "sub_crescimento",
    "sub_complexidade_operacional", "sub_maturidade_digital_baixa",
    "signals", "observacoes", "trigger_event", "playbook",
    "resultado_comercial", "nota_comercial",
    "updated_at",
]
NEWS_COLUMNS = ["company_id", "title", "url", "source", "published_at", "categories", "collected_at"]


def read_df(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    try:
        df = pd.read_excel(path)
        for c in columns:
            if c not in df.columns:
                df[c] = None
        return df
    except Exception:
        return pd.DataFrame(columns=columns)


def write_df(path: Path, df: pd.DataFrame) -> None:
    with _lock:
        df.to_excel(path, index=False)


def upsert(path: Path, rows: list[dict], columns: list[str], key: str | list[str]) -> pd.DataFrame:
    keys = [key] if isinstance(key, str) else key
    df = read_df(path, columns)
    new = pd.DataFrame(rows)
    for c in columns:
        if c not in new.columns:
            new[c] = None
    new = new[columns]
    if df.empty:
        merged = new
    else:
        # Preserva colunas presentes nas duas
        for c in columns:
            if c not in df.columns:
                df[c] = None
        df = df[columns]
        merged = pd.concat([df, new], ignore_index=True)
        merged = merged.drop_duplicates(subset=keys, keep="last")
    write_df(path, merged)
    return merged


def patch_row(path: Path, columns: list[str], key: str, key_value: str, updates: dict) -> bool:
    df = read_df(path, columns)
    if df.empty or key not in df.columns:
        return False
    mask = df[key] == key_value
    if not mask.any():
        return False
    for k, v in updates.items():
        if k not in df.columns:
            df[k] = None
        if df[k].dtype != "object":
            df[k] = df[k].astype("object")
        df.loc[mask, k] = v
    write_df(path, df)
    return True
