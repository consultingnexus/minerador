"""Smoke test do pipeline completo (sem subir o servidor).
Importa 3 empresas, roda os coletores estáveis, gera score e exporta Excel.
"""
import asyncio
from pathlib import Path
from app.services.companies import import_file_bytes, list_companies
from app.services.analyzer import analyze_companies
from app.services.exporter import ranking_df, export_ranking_xlsx


async def main():
    csv = Path("data/sample_companies.csv").read_bytes()
    imported = import_file_bytes("sample_companies.csv", csv)
    print(f"[1] Importadas: {len(imported)}")
    print(list_companies()[["empresa", "cnpj", "site"]].to_string(index=False))

    results = await analyze_companies()
    print(f"\n[2] Analisadas: {len(results)}")
    for r in results:
        print(f"  {r['empresa']:25s} score={r['score']:5.1f} conf={r['confidence']:.2f} "
              f"playbook={r.get('playbook')!r}")
        print(f"    trigger: {r.get('trigger_event')}")

    rdf = ranking_df()
    print(f"\n[3] Ranking df shape: {rdf.shape}")
    print(rdf[["empresa", "score", "confidence", "playbook"]].to_string(index=False))

    out = export_ranking_xlsx()
    print(f"\n[4] Export gerado: {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
