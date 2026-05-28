from __future__ import annotations
import hashlib
import re
from datetime import datetime
from io import BytesIO
import pandas as pd

from app.config import COMPANIES_FILE
from app.utils.storage import read_df, upsert, COMPANY_COLUMNS
from app.models import CompanyIn


def _gen_id(empresa: str, cnpj: str | None, cidade: str | None) -> str:
    if cnpj:
        base = re.sub(r"\D", "", cnpj)
        if len(base) == 14:
            return "cnpj_" + base
    base = f"{(empresa or '').strip().lower()}|{(cidade or '').strip().lower()}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()[:12]


def list_companies() -> pd.DataFrame:
    return read_df(COMPANIES_FILE, COMPANY_COLUMNS)


def add_companies(items: list[CompanyIn]) -> list[dict]:
    now = datetime.utcnow().isoformat()
    rows = []
    for c in items:
        rows.append({
            "id": _gen_id(c.empresa, c.cnpj, c.cidade),
            "empresa": c.empresa,
            "cnpj": (re.sub(r"\D", "", c.cnpj) if c.cnpj else None),
            "setor": c.setor,
            "cnae": None,
            "porte": None,
            "cidade": c.cidade,
            "uf": None,
            "site": c.site,
            "telefone": c.telefone,
            "linkedin": c.linkedin,
            "filiais_count": None,
            "data_abertura": None,
            "created_at": now,
        })
    upsert(COMPANIES_FILE, rows, COMPANY_COLUMNS, key="id")
    return rows


def update_company_meta(company_id: str, meta: dict) -> None:
    """Atualiza campos cadastrais (cnae, porte, uf, data_abertura...) após coletor cnpj."""
    df = read_df(COMPANIES_FILE, COMPANY_COLUMNS)
    if df.empty:
        return
    mask = df["id"] == company_id
    if not mask.any():
        return
    for k, v in meta.items():
        if k not in df.columns or v in (None, ""):
            continue
        # Converte coluna para object (evita LossySetitemError quando dtype era float NaN)
        if df[k].dtype != "object":
            df[k] = df[k].astype("object")
        df.loc[mask, k] = str(v) if not isinstance(v, (int, float)) else v
    df.to_excel(COMPANIES_FILE, index=False)


def import_file_bytes(filename: str, data: bytes) -> list[dict]:
    bio = BytesIO(data)
    if filename.lower().endswith(".csv"):
        df = pd.read_csv(bio)
    else:
        df = pd.read_excel(bio)
    df.columns = [str(c).strip().lower() for c in df.columns]

    items: list[CompanyIn] = []
    for _, row in df.iterrows():
        empresa = _s(row.get("empresa")) or ""
        if not empresa:
            continue
        items.append(CompanyIn(
            empresa=empresa,
            cnpj=_cnpj_str(row.get("cnpj")),
            setor=_s(row.get("setor")),
            cidade=_s(row.get("cidade")),
            site=_s(row.get("site")),
            telefone=_s(row.get("telefone")),
            linkedin=_s(row.get("linkedin")),
        ))
    return add_companies(items)


def _s(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return None
    return s


def _cnpj_str(v) -> str | None:
    """CSV/Excel pode ler CNPJ como int/float. Converte preservando dígitos."""
    if v is None:
        return None
    if isinstance(v, float):
        if v != v:  # NaN
            return None
        v = int(v)
    s = re.sub(r"\D", "", str(v))
    if not s:
        return None
    return s.zfill(14) if len(s) <= 14 else s
