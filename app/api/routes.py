from __future__ import annotations
import math
from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import FileResponse, JSONResponse
import pandas as pd

from app.models import CompanyIn, AnalyzeRequest, CommercialFeedback
from app.services.companies import add_companies, import_file_bytes, list_companies
from app.services.analyzer import analyze_companies
from app.services.exporter import ranking_df, export_ranking_xlsx
from app.services.prospect import run_prospect
from app.collectors.maps_discovery import collect_maps_discovery
from app.utils.storage import patch_row, SCORE_COLUMNS
from app.config import SCORES_FILE, DEFAULT_COLLECTORS, EXPERIMENTAL_COLLECTORS


def _safe_records(df: pd.DataFrame) -> list[dict]:
    """to_dict + saneamento de NaN/inf para JSON."""
    if df.empty:
        return []
    cleaned = df.where(df.notna(), None)
    records = cleaned.to_dict(orient="records")
    for r in records:
        for k, v in list(r.items()):
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                r[k] = None
    return records

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "default_collectors": DEFAULT_COLLECTORS,
        "experimental_collectors": EXPERIMENTAL_COLLECTORS,
    }


@router.post("/companies/import")
async def companies_import(
    file: UploadFile | None = File(default=None),
    companies: list[CompanyIn] | None = Body(default=None),
):
    if file is not None:
        data = await file.read()
        rows = import_file_bytes(file.filename or "upload.xlsx", data)
        return {"imported": len(rows), "companies": rows}
    if companies:
        rows = add_companies(companies)
        return {"imported": len(rows), "companies": rows}
    raise HTTPException(400, "Envie 'file' (multipart) ou body JSON 'companies'.")


@router.post("/companies/analyze")
async def companies_analyze(req: AnalyzeRequest | None = None):
    req = req or AnalyzeRequest()
    results = await analyze_companies(req.company_ids, req.collectors)
    return {"analyzed": len(results), "results": results}


@router.get("/companies/ranking")
async def companies_ranking():
    return JSONResponse(_safe_records(ranking_df()))


@router.get("/companies/export")
async def companies_export():
    path = export_ranking_xlsx()
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )


@router.get("/companies")
async def companies_list():
    return JSONResponse(_safe_records(list_companies()))


@router.post("/prospect/run")
async def prospect_run():
    """Roda as buscas configuradas em config/searches.yaml e devolve um Excel
    com as empresas que não possuem website."""
    path = await run_prospect()
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )


@router.get("/prospect/search")
async def prospect_search(
    setor: str,
    regiao: str,
    max_resultados: int = 30,
):
    """Busca empresas no Google Maps por setor + região e devolve JSON.
    Usado pelo frontend (tabela). Diferente de /prospect/run, que usa a
    config estática e devolve um Excel."""
    setor = (setor or "").strip()
    regiao = (regiao or "").strip()
    if not setor or not regiao:
        raise HTTPException(400, "Informe 'setor' e 'regiao'.")
    max_resultados = max(1, min(int(max_resultados), 100))
    items = await collect_maps_discovery(
        setor=setor, regiao=regiao, max_resultados=max_resultados
    )
    return {
        "setor": setor,
        "regiao": regiao,
        "total": len(items),
        "results": items,
    }


@router.post("/companies/feedback")
async def companies_feedback(fb: CommercialFeedback):
    """Loop de feedback: comercial preenche resultado, persistido no scores.xlsx.
       Permite calibrar pesos depois (sem IA — só análise no pandas)."""
    ok = patch_row(
        SCORES_FILE, SCORE_COLUMNS, key="company_id",
        key_value=fb.company_id,
        updates={"resultado_comercial": fb.resultado, "nota_comercial": fb.nota},
    )
    if not ok:
        raise HTTPException(404, "company_id não encontrado em scores.")
    return {"ok": True}
