"""Coletor de dados cadastrais via BrasilAPI (gratuito, sem chave).

Endpoint: https://brasilapi.com.br/api/cnpj/v1/{cnpj}
Resolve: porte, CNAE, sócios, capital social, situação cadastral, data de abertura.
Para complexidade operacional usa o número de estabelecimentos (matriz + filiais)
via Receita; BrasilAPI retorna 1 estabelecimento por chamada, então também consultamos
o endpoint /cnpj/v1/{raiz}?... NÃO está disponível — usamos heurística sobre o capital
social e porte. Filiais são populadas se o usuário informar manualmente.
"""
from __future__ import annotations
import re
import httpx
from app.collectors.base import CollectorResult
from app.config import HTTP_TIMEOUT, USER_AGENT
from app.utils.logger import get_logger

log = get_logger("collector.cnpj")

BRASILAPI = "https://brasilapi.com.br/api/cnpj/v1/{}"


def _clean(cnpj) -> str:
    if cnpj is None:
        return ""
    return re.sub(r"\D", "", str(cnpj))


async def collect_cnpj(company: dict) -> CollectorResult:
    res = CollectorResult(source="cnpj")
    raw = company.get("cnpj")
    if not raw:
        res.error = "sem_cnpj"
        return res
    cnpj = _clean(raw)
    if len(cnpj) != 14:
        res.error = "cnpj_invalido"
        return res

    url = BRASILAPI.format(cnpj)
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}) as c:
            r = await c.get(url)
        if r.status_code != 200:
            res.error = f"http_{r.status_code}"
            log.warning("BrasilAPI %s -> %s", cnpj, r.status_code)
            return res
        data = r.json()
    except Exception as e:
        res.error = f"erro:{e}"
        log.exception("BrasilAPI falhou: %s", e)
        return res

    cnae_principal = data.get("cnae_fiscal") or data.get("cnae_fiscal_descricao")
    res.meta = {
        "cnpj": cnpj,
        "razao_social": data.get("razao_social"),
        "nome_fantasia": data.get("nome_fantasia"),
        "porte": (data.get("porte") or "").strip() or None,
        "cnae": str(data.get("cnae_fiscal") or "").strip() or None,
        "cnae_descricao": data.get("cnae_fiscal_descricao"),
        "capital_social": data.get("capital_social"),
        "data_abertura": data.get("data_inicio_atividade"),
        "situacao": data.get("descricao_situacao_cadastral"),
        "natureza_juridica": data.get("natureza_juridica"),
        "uf": data.get("uf"),
        "municipio": data.get("municipio"),
        "qsa_count": len(data.get("qsa") or []),
    }
    log.info("cnpj OK %s porte=%s cnae=%s qsa=%d",
             cnpj, res.meta["porte"], res.meta["cnae"], res.meta["qsa_count"])
    return res
