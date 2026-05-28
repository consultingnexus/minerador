from __future__ import annotations
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field

from app.config import SEARCHES_FILE


class SearchSpec(BaseModel):
    setor: str
    regiao: str
    max_resultados: int = Field(default=30, ge=1, le=200)


class ExportCfg(BaseModel):
    arquivo: str = "prospeccao_{timestamp}.xlsx"
    apenas_sem_site: bool = True


class SearchesConfig(BaseModel):
    searches: list[SearchSpec]
    export: ExportCfg = Field(default_factory=ExportCfg)


def load_searches(path: Optional[Path] = None) -> SearchesConfig:
    p = Path(path) if path else SEARCHES_FILE
    if not p.exists():
        raise FileNotFoundError(f"Arquivo de buscas não encontrado: {p}")
    with p.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return SearchesConfig(**raw)
